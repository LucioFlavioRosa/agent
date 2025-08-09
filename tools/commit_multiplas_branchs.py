# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO APRIMORADA)

import json
from github import GithubException
from tools import github_connector

# ==============================================================================
# A FUNÇÃO AUXILIAR FOI ALTERADA PARA LIDAR COM BRANCHES VAZIAS
# ==============================================================================
def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> bool: # [NOVO] A função agora retorna um booleano indicando sucesso.
    print(f"\n--- Processando o Lote para a Branch: '{nome_branch}' ---")

    # [NOVO] Contador para rastrear o número de commits bem-sucedidos.
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
        return False # [ALTERADO] Retorna falso se não houver nada a fazer.

    print("Iniciando a aplicação dos arquivos (um commit por arquivo)...")
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        conteudo = mudanca.get("conteudo")
        justificativa = mudanca.get("justificativa", "")

        if conteudo is None:
            print(f"  [IGNORADO]   Pulando o arquivo '{caminho}' porque seu conteúdo é nulo (None).")
            continue
        if not caminho:
            print(f"  [IGNORADO]   Pulando uma mudança porque não possui caminho de arquivo.")
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

            # [NOVO] Incrementa o contador após um commit bem-sucedido.
            commits_realizados += 1
        except GithubException as e:
            print(f"ERRO ao commitar o arquivo '{caminho}': {e}")
            
    print("Aplicação de commits concluída para esta branch.")

    # [ALTERADO] A criação do PR agora é condicional.
    if commits_realizados > 0:
        # 3. Criação do Pull Request (somente se houver commits)
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            pr_body = descricao_pr if descricao_pr else mensagem_pr
            pr = repo.create_pull(title=mensagem_pr, body=pr_body, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! Acesse em: {pr.html_url}")
            return True # [ALTERADO] Retorna sucesso.
        except GithubException as e:
            if e.status == 422:
                # Trata tanto o caso de "PR já existe" quanto "Sem commits".
                if "A pull request for these commits already exists" in str(e.data.get('message', '')):
                    print(f"AVISO: Um Pull Request para a branch '{nome_branch}' já existe.")
                    return True # Consideramos sucesso, pois o objetivo foi alcançado.
                # O erro "No commits" não deve mais acontecer aqui, mas tratamos por segurança.
                elif "No commits between" in str(e.data.get('errors', [{}])[0].get('message', '')):
                     print(f"AVISO: Nenhum commit novo detectado entre '{branch_alvo_do_pr}' e '{nome_branch}'. Pulando PR.")
                     return True # Não é um erro fatal.
            
            # Re-lança outras exceções para que o chamador saiba que falhou
            print(f"ERRO: Não foi possível criar o Pull Request para '{nome_branch}'. Erro: {e}")
            raise
    else:
        # [NOVO] O que fazer se nenhum commit foi feito.
        print(f"\nNenhum commit foi realizado para a branch '{nome_branch}'. Pulando a criação do Pull Request.")
        return True # Retorna True pois não é um erro, apenas não havia nada a fazer. A branch foi criada e está pronta.


# ==============================================================================
# A FUNÇÃO ORQUESTRADORA FOI AJUSTADA PARA USAR O RETORNO DA FUNÇÃO AUXILIAR
# ==============================================================================
def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados,
    base_branch: str = "main"
):
    """
    Função principal que orquestra a criação de múltiplas branches e PRs
    de forma sequencial e empilhada (stacked).
    """
    try:
        if isinstance(dados_agrupados, str):
            dados_agrupados = json.loads(dados_agrupados)

        print("--- Iniciando o Processo de Pull Requests Empilhados ---")
        repo = github_connector.connection(repositorio=nome_repo)

        branch_anterior = base_branch
        
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            return

        for grupo_atual in lista_de_grupos:
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue

            # [ALTERADO] Captura o resultado da função.
            sucesso_ou_branch_valida = _processar_uma_branch(
                repo=repo,
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,
                branch_alvo_do_pr=branch_anterior,
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_do_pr,
                conjunto_de_mudancas=conjunto_de_mudancas
            )

            # [ALTERADO] A branch base para o próximo PR só é atualizada se a branch atual
            # foi processada com sucesso (ou seja, tem commits ou já existia de forma válida).
            if sucesso_ou_branch_valida:
                branch_anterior = nome_da_branch_atual
            
            print("-" * 60)

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR: {e}")
        raise