import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from typing import Dict, Any, List, Optional
import gitlab

def _is_gitlab_project(repo) -> bool:
    return hasattr(repo, 'web_url') or 'gitlab' in str(type(repo)).lower()

def _processar_uma_branch_gitlab(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote GitLab para a Branch: '{nome_branch}' ---")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # ETAPA 1: Criação da branch empilhada no GitLab
        try:
            # Obter commit SHA da branch de origem
            branch_origem = repo.branches.get(branch_de_origem)
            commit_sha = branch_origem.commit['id']
            
            # Criar nova branch
            repo.branches.create({'branch': nome_branch, 'ref': commit_sha})
            print(f"Branch GitLab '{nome_branch}' criada a partir de '{branch_de_origem}'.")
            
        except gitlab.exceptions.GitlabCreateError as e:
            if "Branch already exists" in str(e) or "already exists" in str(e):
                print(f"AVISO: A branch '{nome_branch}' já existe no GitLab. Commits serão adicionados a ela.")
            else:
                raise

        # ETAPA 2: Aplicação sequencial das mudanças no GitLab
        print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças no GitLab...")
        
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")
            justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

            if not caminho:
                print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
                continue

            try:
                # Verificação de existência do arquivo no GitLab
                arquivo_existente = None
                try:
                    arquivo_existente = repo.files.get(file_path=caminho, ref=nome_branch)
                except gitlab.exceptions.GitlabGetError:
                    pass

                # Processamento diferenciado por status no GitLab
                if status in ("ADICIONADO", "CRIADO"):
                    if arquivo_existente:
                        print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe no GitLab. Será tratado como MODIFICADO.")
                        arquivo_existente.content = conteudo
                        arquivo_existente.save(branch=nome_branch, commit_message=f"refactor: {caminho}")
                    else:
                        repo.files.create({
                            'file_path': caminho,
                            'branch': nome_branch,
                            'content': conteudo,
                            'commit_message': f"feat: {caminho}"
                        })
                        
                    print(f"  [CRIADO/MODIFICADO] {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "MODIFICADO":
                    if not arquivo_existente:
                        print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                        continue
                        
                    arquivo_existente.content = conteudo
                    arquivo_existente.save(branch=nome_branch, commit_message=f"refactor: {caminho}")
                    print(f"  [MODIFICADO] {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "REMOVIDO":
                    if not arquivo_existente:
                        print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                        continue
                        
                    repo.files.delete(file_path=caminho, branch=nome_branch, commit_message=f"refactor: remove {caminho}")
                    print(f"  [REMOVIDO] {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)
                
                else:
                    print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

            except gitlab.exceptions.GitlabError as e:
                print(f"ERRO GitLab ao processar o arquivo '{caminho}': {e}")
            except Exception as e:
                print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
                
        # ETAPA 3: Criação do Merge Request no GitLab
        if commits_realizados > 0:
            try:
                print(f"\nCriando Merge Request GitLab de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                
                mr = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr,
                    'description': descricao_pr
                })
                print(f"Merge Request criado com sucesso! URL: {mr.web_url}")
                resultado_branch.update({"success": True, "pr_url": mr.web_url, "message": "MR criado."})
                
            except gitlab.exceptions.GitlabCreateError as e:
                if "Another open merge request already exists" in str(e):
                    print("AVISO: MR para esta branch já existe.")
                    resultado_branch.update({"success": True, "message": "MR já existente."})
                else:
                    print(f"ERRO ao criar MR para '{nome_branch}': {e}")
                    resultado_branch["message"] = f"Erro ao criar MR: {e}"
        else:
            print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do MR.")
            resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    except Exception as e:
        print(f"ERRO CRÍTICO no processamento da branch GitLab '{nome_branch}': {e}")
        resultado_branch["message"] = f"Erro crítico: {e}"

    return resultado_branch

def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    # Detectar se é GitLab e usar função específica
    if _is_gitlab_project(repo):
        return _processar_uma_branch_gitlab(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    # Função original para GitHub
    print(f"\n--- Processando Lote GitHub para a Branch: '{nome_branch}' ---")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # ETAPA 1: Criação da branch empilhada
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
        
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise

    # ETAPA 2: Aplicação sequencial das mudanças
    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças...")
    
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get("caminho_do_arquivo")
        status = mudanca.get("status", "").upper()
        conteudo = mudanca.get("conteudo")
        justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

        if not caminho:
            print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
            continue

        try:
            # Verificação de existência do arquivo
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass

            # Processamento diferenciado por status
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                    
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                    
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                    
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except GithubException as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
            
    # ETAPA 3: Criação do Pull Request
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            
            pr = repo.create_pull(title=mensagem_pr, body=descricao_pr, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
            resultado_branch.update({"success": True, "pr_url": pr.html_url, "message": "PR criado."})
            
        except GithubException as e:
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                print("AVISO: PR para esta branch já existe.")
                resultado_branch.update({"success": True, "message": "PR já existente."})
            else:
                print(f"ERRO ao criar PR para '{nome_branch}': {e}")
                resultado_branch["message"] = f"Erro ao criar PR: {e.data.get('message', str(e))}"
    else:
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do PR.")
        resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    return resultado_branch


def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados: dict,
    base_branch: str = "main",
    repository_provider: Optional[IRepositoryProvider] = None
) -> List[Dict[str, Any]]:
    resultados_finais = []
    
    try:
        provider_name = type(repository_provider).__name__ if repository_provider else "GitHubRepositoryProvider (padrão)"
        print(f"--- Iniciando o Processo de Pull Requests Empilhados via {provider_name} ---")
        print(f"--- Repositório: {nome_repo} | Base Branch: {base_branch} ---")
        
        # Detectar se é Project ID do GitLab para log específico
        try:
            project_id = int(nome_repo)
            if 'gitlab' in provider_name.lower():
                print(f"--- DETECTADO: GitLab Project ID {project_id} - Suporte completo a múltiplas branches ---")
        except ValueError:
            pass
        
        if repository_provider is None:
            repository_provider = GitHubRepositoryProvider()
            print("AVISO: Nenhum provedor especificado. Usando GitHubRepositoryProvider como padrão.")
        
        connector = GitHubConnector(repository_provider=repository_provider)
        repo = connector.connection(repositorio=nome_repo)
        
        # Log específico para GitLab
        if _is_gitlab_project(repo):
            print(f"--- CONFIRMADO: Repositório GitLab conectado com sucesso ---")
            print(f"--- Branch padrão: {getattr(repo, 'default_branch', 'main')} ---")

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
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
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

            if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                branch_anterior = nome_da_branch_atual
                print(f"Branch '{nome_da_branch_atual}' será usada como base para o próximo grupo.")
            
            print("-" * 60)
        
        return resultados_finais

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]