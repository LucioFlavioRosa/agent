# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO REFATORADA SEGUINDO SOLID)

import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from typing import Dict, Any, List

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
    Processa uma única branch, lida com criação, modificação e remoção
    de arquivos, e cria um Pull Request.
    """
    print(f"\n--- Processando Lote para a Branch: '{nome_branch}' ---")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # Criação da nova branch a partir da branch de origem
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
    except GithubException as e:
        # Tratamento específico para branch já existente
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise

    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças...")
    
    # Processamento de cada mudança no conjunto
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        status = mudanca.get("status", "").upper()
        conteudo = mudanca.get("conteudo")
        justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

        # Validação básica da mudança
        if not caminho:
            print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
            continue

        try:
            # Verificação se o arquivo já existe na branch de destino
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                # Arquivo não existe, sha_arquivo_existente permanece None
                pass

            # Processamento baseado no status da mudança
            if status in ("ADICIONADO", "CRIADO"):
                # Lógica para arquivos novos ou marcados como adicionados
                if sha_arquivo_existente:
                    # Arquivo já existe, trata como modificação
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    # Arquivo não existe, cria novo
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "MODIFICADO":
                # Lógica para arquivos existentes que devem ser modificados
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                # Atualiza o arquivo existente com o novo conteúdo
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "REMOVIDO":
                # Lógica para remoção de arquivos
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                # Remove o arquivo da branch
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            
            else:
                # Status não reconhecido
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except GithubException as e:
            # Tratamento de erros específicos da API GitHub
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            # Tratamento de erros gerais
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
            
    # Criação do Pull Request se houve commits
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            pr = repo.create_pull(title=mensagem_pr, body=descricao_pr, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
            resultado_branch.update({"success": True, "pr_url": pr.html_url, "message": "PR criado."})
        except GithubException as e:
            # Tratamento para PR já existente
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                print("AVISO: PR para esta branch já existe.")
                resultado_branch.update({"success": True, "message": "PR já existente."})
            else:
                print(f"ERRO ao criar PR para '{nome_branch}': {e}")
                resultado_branch["message"] = f"Erro ao criar PR: {e.data.get('message', str(e))}"
    else:
        # Nenhum commit foi realizado
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do PR.")
        resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    return resultado_branch


def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados: dict,
    base_branch: str = "main",
    github_connector: GitHubConnector = None
) -> List[Dict[str, Any]]:
    """
    Função principal refatorada seguindo princípios SOLID.
    Agora aceita injeção de dependência do GitHubConnector.
    """
    resultados_finais = []
    try:
        print("--- Iniciando o Processo de Pull Requests Empilhados ---")
        
        # Usa o conector injetado ou cria um com dependências padrão
        connector = github_connector or GitHubConnector.create_with_defaults()
        repo = connector.connection(repositorio=nome_repo)

        # Configuração inicial para PRs empilhados
        # Cada PR é criado a partir da branch anterior, criando uma cadeia
        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            return []

        # Processamento sequencial de cada grupo de mudanças
        for grupo_atual in lista_de_grupos:
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            # Validação do grupo atual
            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                continue

            # Processamento da branch atual
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

            # Atualização da branch base para o próximo PR (empilhamento)
            # Se o PR foi criado com sucesso, a próxima branch será criada a partir desta
            if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                branch_anterior = nome_da_branch_atual
            
            print("-" * 60)
        
        return resultados_finais

    except Exception as e:
        # Tratamento de erros fatais no orquestrador
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]