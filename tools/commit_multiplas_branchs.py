import traceback
from github import GithubException, UnknownObjectException, Repository
from typing import Dict, Any, List

# --- FUNÇÃO AUXILIAR REUTILIZÁVEL ---
# Esta função contém a lógica central de fazer commits, que é a mesma para ambos os fluxos.
def _commitar_arquivos_na_branch(repo: Repository.Repository, nome_branch: str, conjunto_de_mudancas: list) -> tuple[int, list[str]]:
    """
    Aplica uma lista de mudanças (criar, modificar, remover) a uma branch específica.
    Retorna o número de commits e a lista de arquivos afetados.
    """
    commits_realizados = 0
    arquivos_modificados = []
    
    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças na branch '{nome_branch}'...")
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        status = mudanca.get("status", "").upper()
        conteudo = mudanca.get("conteudo")

        if not caminho:
            continue

        try:
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass # Arquivo não existe, o que é esperado para CRIADO/ADICIONADO

            commit_message = f"feat: Adiciona {caminho}" if status in ("ADICIONADO", "CRIADO") else f"refactor: Atualiza {caminho}"
            if status == "REMOVIDO":
                commit_message = f"refactor: Remove {caminho}"
            
            # Lógica de Ação
            if status in ("ADICIONADO", "CRIADO"):
                if conteudo is None: continue
                if sha_arquivo_existente:
                    repo.update_file(path=caminho, message=commit_message, content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    repo.create_file(path=caminho, message=commit_message, content=conteudo, branch=nome_branch)
            elif status == "MODIFICADO":
                if conteudo is None or not sha_arquivo_existente: continue
                repo.update_file(path=caminho, message=commit_message, content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
            elif status == "REMOVIDO":
                if not sha_arquivo_existente: continue
                repo.delete_file(path=caminho, message=commit_message, sha=sha_arquivo_existente, branch=nome_branch)
            else: # Ignora "INALTERADO" e outros status
                continue
            
            print(f"  [{status}] {caminho}")
            commits_realizados += 1
            arquivos_modificados.append(caminho)

        except Exception as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e}")
            
    return commits_realizados, arquivos_modificados


# --- FUNÇÃO PÚBLICA 1: COMMIT DIRETO (NOVA) ---
def commit_direto_na_main(repo: Repository.Repository, dados_agrupados: dict) -> List[Dict[str, Any]]:
    """
    Pega todas as mudanças de todos os grupos e as comita diretamente
    na branch padrão do repositório.
    """
    print("\n--- INICIANDO MODO DE COMMIT DIRETO ---")
    try:
        todas_as_mudancas = []
        for grupo in dados_agrupados.get("grupos", []):
            todas_as_mudancas.extend(grupo.get("conjunto_de_mudancas", []))

        if not todas_as_mudancas:
            print("Nenhuma mudança real encontrada para commitar.")
            return [{"success": True, "message": "Nenhuma mudança para commitar."}]

        branch_alvo = repo.default_branch
        commits_realizados, arquivos_modificados = _commitar_arquivos_na_branch(repo, branch_alvo, todas_as_mudancas)
        
        return [{
            "branch_name": branch_alvo,
            "success": True,
            "pr_url": None, # Nenhum PR é criado
            "message": f"{commits_realizados} arquivos commitados diretamente em '{branch_alvo}'.",
            "arquivos_modificados": arquivos_modificados
        }]
    except Exception as e:
        print(f"ERRO FATAL DURANTE O COMMIT DIRETO: {e}")
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal: {e}"}]


# --- FUNÇÃO PÚBLICA 2: PULL REQUESTS EMPILHADOS ---
def criar_pull_requests_empilhados(repo: Repository.Repository, dados_agrupados: dict, base_branch: str = "main") -> List[Dict[str, Any]]:
    """
    Cria uma branch e um Pull Request para cada grupo de mudanças.
    """
    print("\n--- INICIANDO MODO DE PULL REQUESTS EMPILHADOS ---")
    try:
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

            print(f"\n--- Processando grupo para a branch: '{nome_da_branch_atual}' ---")
            
            resultado_da_branch = {
                "branch_name": nome_da_branch_atual, "success": True, "pr_url": None,
                "message": "Nenhuma mudança para commitar.", "arquivos_modificados": []
            }

            try:
                ref_base = repo.get_git_ref(f"heads/{branch_anterior}")
                repo.create_git_ref(ref=f"refs/heads/{nome_da_branch_atual}", sha=ref_base.object.sha)
                print(f"Branch '{nome_da_branch_atual}' criada a partir de '{branch_anterior}'.")
            except GithubException as e:
                if e.status == 422 and "Reference already exists" in str(e.data):
                    print(f"AVISO: A branch '{nome_da_branch_atual}' já existe.")
                else: raise

            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])
            commits_realizados, arquivos_modificados = _commitar_arquivos_na_branch(repo, nome_da_branch_atual, conjunto_de_mudancas)
            resultado_da_branch["arquivos_modificados"] = arquivos_modificados

            if commits_realizados > 0:
                try:
                    pr = repo.create_pull(
                        title=grupo_atual.get("titulo_pr", "Refatoração Automática"),
                        body=grupo_atual.get("resumo_do_pr", ""),
                        head=nome_da_branch_atual,
                        base=base_branch # Todos os PRs apontam para a branch base
                    )
                    print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
                    resultado_da_branch.update({"pr_url": pr.html_url, "message": "PR criado."})
                except GithubException as e:
                    if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                        print("AVISO: PR para esta branch já existe.")
                        resultado_da_branch["message"] = "PR já existente."
                    else:
                        resultado_da_branch["success"] = False
                        resultado_da_branch["message"] = f"Erro ao criar PR: {e.data.get('message', str(e))}"
            
            resultados_finais.append(resultado_da_branch)

            if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                branch_anterior = nome_da_branch_atual
        
        return resultados_finais
    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE PRS: {e}")
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal: {e}"}]
