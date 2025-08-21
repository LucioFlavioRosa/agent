import traceback
from github import GithubException, UnknownObjectException, Repository
from typing import Dict, Any, List

def _commitar_arquivos_na_branch(repo: Repository.Repository, nome_branch: str, conjunto_de_mudancas: list) -> tuple[int, list[str]]:
    """
    Função auxiliar genérica que aplica uma lista de mudanças (criar, modificar, remover)
    a uma branch específica. Retorna o número de commits e a lista de arquivos modificados.
    """
    commits_realizados = 0
    arquivos_modificados = []
    
    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças na branch '{nome_branch}'...")
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        status = mudanca.get("status", "").upper()
        conteudo = mudanca.get("conteudo") # Pode ser None para REMOVIDO
        justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

        if not caminho:
            print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
            continue

        try:
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass # Arquivo não existe, o que é esperado para CRIADO/ADICIONADO

            commit_message = f"feat: {caminho}" if status in ("ADICIONADO", "CRIADO") else f"refactor: {caminho}"
            if status == "REMOVIDO":
                commit_message = f"refactor: remove {caminho}"

            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    print(f"  [MODIFICANDO] Arquivo '{caminho}' que deveria ser novo já existe. Atualizando...")
                    repo.update_file(path=caminho, message=commit_message, content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    repo.create_file(path=caminho, message=commit_message, content=conteudo, branch=nome_branch)
                print(f"  [CRIADO] {caminho}")
                commits_realizados += 1
                arquivos_modificados.append(caminho)

            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado. Ignorando.")
                    continue
                repo.update_file(path=caminho, message=commit_message, content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                arquivos_modificados.append(caminho)

            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                repo.delete_file(path=caminho, message=commit_message, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                arquivos_modificados.append(caminho)
            
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except GithubException as e:
            print(f"ERRO de API ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
            
    return commits_realizados, arquivos_modificados


def _processar_uma_branch_com_pr(
    repo: Repository.Repository,
    nome_branch: str,
    branch_de_origem: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    """
    Processa uma única branch, realiza os commits e cria um Pull Request.
    """
    print(f"\n--- Processando Lote para a Branch: '{nome_branch}' (Modo PR) ---")
    
    resultado_branch = {
        "branch_name": nome_branch, "success": False, "pr_url": None, "message": "", "arquivos_modificados": []
    }

    try:
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else: raise

    commits_realizados, arquivos_modificados = _commitar_arquivos_na_branch(repo, nome_branch, conjunto_de_mudancas)
    resultado_branch["arquivos_modificados"] = arquivos_modificados
    
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_de_origem}'...")
            pr = repo.create_pull(title=mensagem_pr, body=descricao_pr, head=nome_branch, base=branch_de_origem)
            print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
            resultado_branch.update({"success": True, "pr_url": pr.html_url, "message": "PR criado."})
        except GithubException as e:
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                print("AVISO: PR para esta branch já existe.")
                resultado_branch.update({"success": True, "message": "PR já existente."})
            else:
                resultado_branch["message"] = f"Erro ao criar PR: {e.data.get('message', str(e))}"
    else:
        print(f"\nNenhum commit realizado. Pulando criação do PR.")
        resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    return resultado_branch


def processar_e_subir_mudancas_agrupadas(
    repo: Repository.Repository,
    dados_agrupados: dict,
    repo_foi_criado_agora: bool,
    base_branch: str = "main"
) -> List[Dict[str, Any]]:
    """
    Função principal que orquestra a criação de branches e PRs ou faz commit direto.
    """
    try:
        # --- LÓGICA DE DECISÃO PRINCIPAL ---
        if repo_foi_criado_agora:
            print("\n--- MODO DE COMMIT DIRETO (REPOSITÓRIO NOVO) ---")
            
            todas_as_mudancas = []
            for grupo in dados_agrupados.get("grupos", []):
                todas_as_mudancas.extend(grupo.get("conjunto_de_mudancas", []))

            if not todas_as_mudancas:
                print("Nenhuma mudança encontrada para commitar.")
                return [{"success": True, "message": "Nenhuma mudança para commitar."}]

            branch_alvo = repo.default_branch
            commits_realizados, arquivos_modificados = _commitar_arquivos_na_branch(repo, branch_alvo, todas_as_mudancas)
            
            return [{
                "branch_name": branch_alvo,
                "success": True,
                "pr_url": None,
                "message": f"{commits_realizados} arquivos commitados diretamente em '{branch_alvo}'.",
                "arquivos_modificados": arquivos_modificados
            }]

        else:
            # --- FLUXO PADRÃO DE PULL REQUESTS EMPILHADOS ---
            print("\n--- MODO DE PULL REQUESTS (REPOSITÓRIO EXISTENTE) ---")
            resultados_finais = []
            branch_anterior = base_branch
            lista_de_grupos = dados_agrupados.get("grupos", [])
            
            if not lista_de_grupos:
                print("Nenhum grupo de mudanças encontrado para processar.")
                return []

            for grupo_atual in lista_de_grupos:
                nome_da_branch_atual = grupo_atual.get("branch_sugerida")
                if not nome_da_branch_atual:
                    print("AVISO: Grupo ignorado por não ter uma 'branch_sugerida'.")
                    continue
                
                resultado_da_branch = _processar_uma_branch_com_pr(
                    repo=repo,
                    nome_branch=nome_da_branch_atual,
                    branch_de_origem=branch_anterior,
                    mensagem_pr=grupo_atual.get("titulo_pr", "Refatoração Automática"),
                    descricao_pr=grupo_atual.get("resumo_do_pr", ""),
                    conjunto_de_mudancas=grupo_atual.get("conjunto_de_mudancas", [])
                )
                
                resultados_finais.append(resultado_da_branch)

                if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                    branch_anterior = nome_da_branch_atual
                
                print("-" * 60)
            
            return resultados_finais

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]
