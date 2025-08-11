# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO API-PURA + JOB_STORE)

import json
from github import GithubException
from . import github_connector

# [NOVO] Importa as funções de comunicação com o Redis
from .job_store import get_job, set_job

# ==============================================================================
# A FUNÇÃO AUXILIAR AGORA RECEBE O job_id PARA REPORTAR O PROGRESSO
# ==============================================================================
def _processar_uma_branch(
    repo,
    job_id: str, # [NOVO] Adicionado job_id como parâmetro
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> bool:
    print(f"\n--- Processando o Lote para a Branch: '{nome_branch}' ---")
    commits_realizados = 0

    # 1. Criação da Branch
    print(f"Criando ou reutilizando a branch '{nome_branch}' a partir de '{branch_de_origem}'...")
    try:
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada com sucesso.")
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Os commits serão adicionados a ela.")
        else:
            raise

    # 2. Loop de Commits
    if not conjunto_de_mudancas:
        print("Nenhuma mudança para aplicar nesta branch.")
        return False

    print("Iniciando a aplicação dos arquivos (um commit por arquivo)...")
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        conteudo = mudanca.get("conteudo") # [NOTA] Este 'conteudo' deve corresponder ao 'novo_conteudo' gerado pela IA
        justificativa = mudanca.get("justificativa", "")

        if conteudo is None or not caminho:
            print(f"  [IGNORADO] Pulando mudança incompleta: {mudanca}")
            continue

        sha_arquivo_existente = None
        try:
            arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
            sha_arquivo_existente = arquivo_existente.sha
        except GithubException as e:
            if e.status != 404:
                print(f"ERRO ao verificar o arquivo '{caminho}': {e}")
                continue
        
        try:
            assunto_commit = f"feat: {caminho}" if not sha_arquivo_existente else f"refactor: {caminho}"
            commit_message_completo = f"{assunto_commit}\n\n{justificativa}"

            if sha_arquivo_existente:
                repo.update_file(path=caminho, message=commit_message_completo, content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
            else:
                repo.create_file(path=caminho, message=commit_message_completo, content=conteudo, branch=nome_branch)
                print(f"  [CRIADO]     {caminho}")
            
            commits_realizados += 1
        except GithubException as e:
            print(f"ERRO ao commitar o arquivo '{caminho}': {e}")
            
    print("Aplicação de commits concluída para esta branch.")

    if commits_realizados > 0:
        # 3. Criação do Pull Request
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            pr_body = descricao_pr if descricao_pr else mensagem_pr
            pr = repo.create_pull(title=mensagem_pr, body=pr_body, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! Acesse em: {pr.html_url}")

            # [NOVO] Salva o link do PR no Redis
            job_info = get_job(job_id)
            if job_info:
                link_info = {"branch": nome_branch, "url": pr.html_url}
                if 'commit_links' not in job_info['data']:
                    job_info['data']['commit_links'] = []
                job_info['data']['commit_links'].append(link_info)
                set_job(job_id, job_info)

            return True
        except GithubException as e:
            if e.status == 422:
                if "A pull request for these commits already exists" in str(e.data.get('message', '')):
                    print(f"AVISO: Um Pull Request para a branch '{nome_branch}' já existe.")
                    return True 
                elif "No commits between" in str(e.data.get('errors', [{}])[0].get('message', '')):
                    print(f"AVISO: Nenhum commit novo detectado. Pulando PR.")
                    return True
            
            print(f"ERRO: Não foi possível criar o Pull Request para '{nome_branch}'. Erro: {e}")
            raise
    else:
        print(f"\nNenhum commit foi realizado para a branch '{nome_branch}'. Pulando a criação do Pull Request.")
        return True


# ==============================================================================
# A FUNÇÃO ORQUESTRADORA AGORA PASSA O job_id PARA A FUNÇÃO AUXILIAR
# ==============================================================================
def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados,
    job_id: str # [ALTERADO] Recebe job_id do backend
):
    """
    Função principal que orquestra a criação de múltiplas branches e PRs
    de forma sequencial e empilhada (stacked), reportando o progresso.
    """
    try:
        # [NOTA] Verifique se os dados da IA estão no formato correto.
        # A sua versão anterior esperava a chave 'conteudo', enquanto a IA pode gerar 'novo_conteudo'.
        # Se necessário, adicione uma etapa aqui para padronizar os dados.
        if isinstance(dados_agrupados, str):
            dados_agrupados_str = dados_agrupados.replace("'conteudo'", "'novo_conteudo'")
            dados_agrupados = json.loads(dados_agrupados_str)

        print("--- Iniciando o Processo de Pull Requests Empilhados (API-Pura) ---")
        repo = github_connector.connection(repositorio=nome_repo)
        branch_anterior = repo.default_branch
        
        for grupo_atual in dados_agrupados.get("grupos", []):
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            
            # [NOTA] Aqui garantimos a compatibilidade dos nomes das chaves
            conjunto_de_mudancas = []
            for mudanca in grupo_atual.get("conjunto_de_mudancas", []):
                mudanca['conteudo'] = mudanca.get('conteudo', mudanca.get('novo_conteudo'))
                conjunto_de_mudancas.append(mudanca)

            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue

            sucesso_ou_branch_valida = _processar_uma_branch(
                repo=repo,
                job_id=job_id, # [NOVO] Passa o job_id
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,
                branch_alvo_do_pr=branch_anterior,
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_do_pr,
                conjunto_de_mudancas=conjunto_de_mudancas
            )

            if sucesso_ou_branch_valida:
                branch_anterior = nome_da_branch_atual
            
            print("-" * 60)

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR: {e}")
        job_info = get_job(job_id)
        if job_info:
            job_info['error'] = f"Falha durante o commit via API: {e}"
            job_info['status'] = 'failed'
            set_job(job_id, job_info)
        raise
