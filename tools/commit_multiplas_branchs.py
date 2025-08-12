# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO COM VERIFICAÇÃO DE MUDANÇAS)

import json
from github import GithubException
from tools import github_connector
from typing import Dict, Any, Optional, List

# ==============================================================================
# A FUNÇÃO AUXILIAR _processar_uma_branch NÃO PRECISA DE MUDANÇAS.
# ==============================================================================
def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    """
    Processa uma única branch, realiza os commits e cria um Pull Request.
    Retorna um dicionário com os detalhes da operação.
    """
    print(f"\n--- Processando o Lote para a Branch: '{nome_branch}' ---")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": ""
    }

    commits_realizados = 0

    # 1. Criação da Branch
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
    print("Iniciando a aplicação dos arquivos (um commit por arquivo)...")
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        conteudo = mudanca.get("conteudo")
        justificativa = mudanca.get("justificativa", "")

        if conteudo is None or not caminho:
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

    # 3. Criação do Pull Request (somente se houver commits)
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            pr_body = descricao_pr if descricao_pr else mensagem_pr
            pr = repo.create_pull(title=mensagem_pr, body=pr_body, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! Acesse em: {pr.html_url}")
            
            resultado_branch["success"] = True
            resultado_branch["pr_url"] = pr.html_url
            resultado_branch["message"] = f"Pull Request criado com sucesso."
            
        except GithubException as e:
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data.get('message', '')):
                print(f"AVISO: Um Pull Request para a branch '{nome_branch}' já existe. Buscando link...")
                prs_existentes = repo.get_pulls(state='open', head=f'{repo.owner.login}:{nome_branch}', base=branch_alvo_do_pr)
                pr_encontrado = prs_existentes[0] if prs_existentes.totalCount > 0 else None
                
                if pr_encontrado:
                    resultado_branch["success"] = True
                    resultado_branch["pr_url"] = pr_encontrado.html_url
                    resultado_branch["message"] = "Um Pull Request para esta branch já existia."
                else:
                    resultado_branch["success"] = True
                    resultado_branch["message"] = "API indicou que o PR já existe, mas não foi possível encontrar o link."
            else:
                print(f"ERRO: Não foi possível criar o Pull Request para '{nome_branch}'. Erro: {e}")
                raise
    else:
        print(f"\nNenhum commit foi realizado para a branch '{nome_branch}'. Pulando a criação do Pull Request.")
        resultado_branch["success"] = True
        resultado_branch["message"] = "Nenhum commit realizado, PR não foi necessário."

    return resultado_branch


# ==============================================================================
# A FUNÇÃO ORQUESTRADORA AGORA VERIFICA SE HÁ MUDANÇAS ANTES DE PROCESSAR
# ==============================================================================
def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados,
    base_branch: str = "main"
) -> List[Dict[str, Any]]:
    """
    Função principal que orquestra a criação de múltiplas branches e PRs
    e retorna uma lista com os resultados de cada uma.
    """
    resultados_finais = []

    try:
        if isinstance(dados_agrupados, str):
            dados_agrupados = json.loads(dados_agrupados)

        print("--- Iniciando o Processo de Pull Requests Empilhados ---")
        repo = github_connector.connection(repositorio=nome_repo)

        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            return []

        for grupo_atual in lista_de_grupos:
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            # [NOVO] Verificação para pular grupos que não têm nenhuma mudança.
            # Isso evita a criação de branches vazias.
            if not conjunto_de_mudancas:
                print(f"\nAVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                print("-" * 60)
                continue

            resultado_da_branch = _processar_uma_branch(
                repo=repo,
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,
                branch_alvo_do_pr=branch_anterior,
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_do_pr,
                conjunto_de_mudancas=conjunto_de_mudancas
            )
            
            resultados_finais.append(resultado_da_branch)

            if resultado_da_branch["success"]:
                branch_anterior = nome_da_branch_atual
            
            print("-" * 60)
        
        return resultados_finais

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR: {e}")
        resultados_finais.append({"success": False, "message": f"Erro fatal no orquestrador: {e}"})
        return resultados_finais
