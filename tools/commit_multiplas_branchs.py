import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from typing import Dict, Any, List, Optional

def _is_gitlab_project(repo) -> bool:
    return hasattr(repo, 'web_url') or 'gitlab' in str(type(repo)).lower()

def _is_azure_repo(repo) -> bool:
    return hasattr(repo, '_provider_type') and repo._provider_type == 'azure_devops'

def _processar_uma_branch_azure(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote Azure DevOps para a Branch: '{nome_branch}' ---")
    print(f"[DEBUG][AZURE] Tipo do objeto repo: {type(repo)}")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        import requests
        import base64
        
        organization = repo._organization
        project = repo._project
        repository = repo._repository
        
        from tools.github_connector import GitHubConnector
        connector = GitHubConnector.create_with_defaults()
        token = connector._get_token_for_org(organization, 'azure')
        
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"
        }
        
        print(f"[DEBUG][AZURE] Obtendo referência da branch de origem: {branch_de_origem}")
        refs_url = f"{base_url}/git/repositories/{repository}/refs?filter=heads/{branch_de_origem}&api-version=7.0"
        refs_response = requests.get(refs_url, headers=headers, timeout=30)
        
        if refs_response.status_code != 200:
            raise Exception(f"Erro ao obter referência da branch {branch_de_origem}: {refs_response.text}")
        
        refs_data = refs_response.json()
        if not refs_data.get('value'):
            raise Exception(f"Branch {branch_de_origem} não encontrada")
        
        source_commit_id = refs_data['value'][0]['objectId']
        print(f"[DEBUG][AZURE] Commit ID da branch origem: {source_commit_id}")
        
        print(f"[DEBUG][AZURE] Criando branch: {nome_branch}")
        create_branch_url = f"{base_url}/git/repositories/{repository}/refs?api-version=7.0"
        create_branch_payload = [{
            "name": f"refs/heads/{nome_branch}",
            "oldObjectId": "0000000000000000000000000000000000000000",
            "newObjectId": source_commit_id
        }]
        
        branch_response = requests.post(create_branch_url, headers=headers, json=create_branch_payload, timeout=30)
        if branch_response.status_code not in [200, 201]:
            if "already exists" in branch_response.text.lower():
                print(f"AVISO: A branch Azure '{nome_branch}' já existe. Commits serão adicionados a ela.")
                current_commit_id = source_commit_id
            else:
                raise Exception(f"Erro ao criar branch: {branch_response.text}")
        else:
            current_commit_id = source_commit_id
        
        changes = []
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")
            
            if not caminho:
                continue
                
            change_item = {
                "changeType": "edit",
                "item": {"path": f"/{caminho}"},
                "newContent": {
                    "content": conteudo or "",
                    "contentType": "rawtext"
                }
            }
            
            if status in ("ADICIONADO", "CRIADO"):
                change_item["changeType"] = "add"
            elif status == "MODIFICADO":
                change_item["changeType"] = "edit"
            elif status == "REMOVIDO":
                change_item["changeType"] = "delete"
                del change_item["newContent"]
            
            changes.append(change_item)
            resultado_branch["arquivos_modificados"].append(caminho)
        
        if not changes:
            print(f"\nNenhuma mudança para commitar na branch Azure '{nome_branch}'.")
            resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})
            return resultado_branch
        
        print(f"[DEBUG][AZURE] Criando commit com {len(changes)} mudanças")
        push_url = f"{base_url}/git/repositories/{repository}/pushes?api-version=7.0"
        push_payload = {
            "refUpdates": [{
                "name": f"refs/heads/{nome_branch}",
                "oldObjectId": current_commit_id
            }],
            "commits": [{
                "comment": f"Refatoração automática: {mensagem_pr}",
                "changes": changes
            }]
        }
        
        push_response = requests.post(push_url, headers=headers, json=push_payload, timeout=30)
        if push_response.status_code not in [200, 201]:
            raise Exception(f"Erro ao fazer push: {push_response.text}")
        
        commits_realizados = len(changes)
        print(f"[DEBUG][AZURE] Commit realizado com sucesso. {commits_realizados} arquivos modificados.")
        
        print(f"[DEBUG][AZURE] Criando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'")
        pr_url = f"{base_url}/git/repositories/{repository}/pullrequests?api-version=7.0"
        pr_payload = {
            "sourceRefName": f"refs/heads/{nome_branch}",
            "targetRefName": f"refs/heads/{branch_alvo_do_pr}",
            "title": mensagem_pr,
            "description": descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
        }
        
        pr_response = requests.post(pr_url, headers=headers, json=pr_payload, timeout=30)
        if pr_response.status_code in [200, 201]:
            pr_data = pr_response.json()
            pr_web_url = f"https://dev.azure.com/{organization}/{project}/_git/{repository}/pullrequest/{pr_data['pullRequestId']}"
            print(f"Pull Request Azure criado com sucesso! URL: {pr_web_url}")
            resultado_branch.update({"success": True, "pr_url": pr_web_url, "message": "PR criado."})
        else:
            if "already exists" in pr_response.text.lower():
                print(f"AVISO: PR para esta branch Azure já existe.")
                resultado_branch.update({"success": True, "message": "PR já existente."})
            else:
                print(f"ERRO ao criar PR Azure: {pr_response.text}")
                resultado_branch["message"] = f"Erro ao criar PR: {pr_response.text}"
        
    except Exception as e:
        print(f"[ERRO][AZURE] ERRO FATAL ao processar branch Azure '{nome_branch}': {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        resultado_branch["message"] = f"Erro fatal: {e}"
    
    print(f"[DEBUG][AZURE] Resultado final da branch {nome_branch}: {resultado_branch}")
    return resultado_branch

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
    print(f"[DEBUG][GITLAB] Tipo do objeto repo: {type(repo)}")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        print(f"[DEBUG][GITLAB] Iniciando criação da branch: {nome_branch} a partir de {branch_de_origem}")
        try:
            print(f"[DEBUG][GITLAB] Chamando repo.branches.create com parâmetros: {{'branch': '{nome_branch}', 'ref': '{branch_de_origem}'}}")
            repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
            print(f"[DEBUG][GITLAB] Branch GitLab '{nome_branch}' criada com sucesso.")
        except Exception as e:
            print(f"[DEBUG][GITLAB] Exceção ao criar branch: {type(e).__name__}: {str(e)}")
            if "already exists" in str(e).lower():
                print(f"AVISO: A branch GitLab '{nome_branch}' já existe. Commits serão adicionados a ela.")
            else:
                print(f"[ERRO][GITLAB] Falha crítica ao criar branch: {e}")
                raise

        print(f"[DEBUG][GITLAB] Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças no GitLab...")
        
        for i, mudanca in enumerate(conjunto_de_mudancas):
            print(f"[DEBUG][GITLAB] Processando mudança {i+1}/{len(conjunto_de_mudancas)}")
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")

            print(f"[DEBUG][GITLAB] Mudança: arquivo='{caminho}', status='{status}', conteudo_length={len(conteudo) if conteudo else 0}")

            if not caminho:
                print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
                continue

            try:
                if status in ("ADICIONADO", "CRIADO"):
                    print(f"[DEBUG][GITLAB] Chamando repo.files.create para {caminho}")
                    dados_criacao = {
                        'file_path': caminho,
                        'branch': nome_branch,
                        'content': conteudo or "",
                        'commit_message': f"feat: Cria {caminho}"
                    }
                    repo.files.create(dados_criacao)
                    print(f"  [CRIADO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "MODIFICADO":
                    print(f"[DEBUG][GITLAB] Buscando arquivo para modificar: {caminho}")
                    arquivo = repo.files.get(file_path=caminho, ref=nome_branch)
                    arquivo.content = conteudo or ""
                    arquivo.save(branch=nome_branch, commit_message=f"refactor: Modifica {caminho}")
                    print(f"  [MODIFICADO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "REMOVIDO":
                    print(f"[DEBUG][GITLAB] Chamando repo.files.delete para {caminho}")
                    repo.files.delete(file_path=caminho,
                                      branch=nome_branch,
                                      commit_message=f"refactor: Remove {caminho}")
                    print(f"  [REMOVIDO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)
                
                else:
                    print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo GitLab '{caminho}'. Ignorando.")

            except Exception as file_e:
                print(f"[ERRO][GITLAB] Erro ao processar o arquivo '{caminho}': {type(file_e).__name__}: {file_e}")
                import traceback
                traceback.print_exc()
            
        print(f"[DEBUG][GITLAB] Commits realizados: {commits_realizados}")
        if commits_realizados > 0:
            try:
                print(f"\n[DEBUG][GITLAB] Criando Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                mr_result = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr,
                    'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
                })
                mr_url = getattr(mr_result, 'web_url', 'URL não disponível')
                print(f"Merge Request GitLab criado com sucesso! URL: {mr_url}")
                resultado_branch.update({"success": True, "pr_url": mr_url, "message": "MR criado."})
                
            except Exception as mr_e:
                print(f"[ERRO][GITLAB] Exceção ao criar MR: {type(mr_e).__name__}: {mr_e}")
                if "already exists" in str(mr_e).lower():
                    mrs = repo.mergerequests.list(state='opened', source_branch=nome_branch, target_branch=branch_alvo_do_pr)
                    mr_url = mrs[0].web_url if mrs else "URL não encontrada"
                    print(f"AVISO: MR para esta branch GitLab já existe. URL: {mr_url}")
                    resultado_branch.update({"success": True, "pr_url": mr_url, "message": "MR já existente."})
                else:
                    print(f"ERRO ao criar MR GitLab para '{nome_branch}': {mr_e}")
                    resultado_branch["message"] = f"Erro ao criar MR: {mr_e}"
        else:
            print(f"\nNenhum commit realizado para a branch GitLab '{nome_branch}'. Pulando criação do MR.")
            resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    except Exception as e:
        print(f"[ERRO][GITLAB] ERRO FATAL ao processar branch GitLab '{nome_branch}': {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        resultado_branch["message"] = f"Erro fatal: {e}"

    print(f"[DEBUG][GITLAB] Resultado final da branch {nome_branch}: {resultado_branch}")
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
    if _is_azure_repo(repo):
        print(f"[DEBUG] Detectado repositório Azure DevOps, delegando para fluxo específico")
        return _processar_uma_branch_azure(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    if _is_gitlab_project(repo):
        print(f"[DEBUG] Detectado repositório GitLab, delegando para fluxo específico")
        return _processar_uma_branch_gitlab(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
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
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
        
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise

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
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass
            
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo or "", branch=nome_branch)
                    
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                    
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)
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
            
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            
            pr = repo.create_pull(title=mensagem_pr, body=descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA.", head=nome_branch, base=branch_alvo_do_pr)
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
    print(f"[DEBUG] ENTRADA processar_e_subir_mudancas_agrupadas:")
    print(f"[DEBUG]   nome_repo: {nome_repo}")
    print(f"[DEBUG]   base_branch: {base_branch}")
    print(f"[DEBUG]   repository_provider: {type(repository_provider).__name__ if repository_provider else None}")
    print(f"[DEBUG]   dados_agrupados keys: {list(dados_agrupados.keys()) if dados_agrupados else 'None'}")
    print(f"[DEBUG]   número de grupos: {len(dados_agrupados.get('grupos', []))}")
    
    resultados_finais = []
    
    try:
        provider_name = type(repository_provider).__name__ if repository_provider else "GitHubRepositoryProvider (padrão)"
        print(f"--- Iniciando o Processo de Pull Requests Empilhados via {provider_name} ---")
        
        if repository_provider is None:
            repository_provider = GitHubRepositoryProvider()
            print("AVISO: Nenhum provedor especificado. Usando GitHubRepositoryProvider como padrão.")
        
        print(f"[DEBUG] Criando GitHubConnector com provider: {type(repository_provider).__name__}")
        connector = GitHubConnector(repository_provider=repository_provider)
        
        repository_type = 'github'
        if 'GitLab' in provider_name:
            repository_type = 'gitlab'
        elif 'Azure' in provider_name:
            repository_type = 'azure'
        
        print(f"[DEBUG] Estabelecendo conexão com repositório: {nome_repo} (tipo: {repository_type})")
        repo = connector.connection(repositorio=nome_repo, repository_type=repository_type)
        print(f"[DEBUG] Conexão estabelecida. Tipo do objeto repo: {type(repo)}")
        
        repo_type = "Azure DevOps" if _is_azure_repo(repo) else "GitLab" if _is_gitlab_project(repo) else "GitHub"
        print(f"Tipo de repositório detectado: {repo_type}")

        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas: []")
            return []

        for i, grupo_atual in enumerate(lista_de_grupos):
            print(f"[DEBUG] Processando grupo {i+1}/{len(lista_de_grupos)}")
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            print(f"[DEBUG]   branch_sugerida: {nome_da_branch_atual}")
            print(f"[DEBUG]   titulo_pr: {resumo_do_pr}")
            print(f"[DEBUG]   número de mudanças: {len(conjunto_de_mudancas)}")

            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                continue

            print(f"[DEBUG] Chamando _processar_uma_branch para {nome_da_branch_atual}")
            resultado_da_branch = _processar_uma_branch(
                repo=repo,
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,
                branch_alvo_do_pr=branch_anterior,
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_do_pr,
                conjunto_de_mudancas=conjunto_de_mudancas
            )
            print(f"[DEBUG] Resultado da branch {nome_da_branch_atual}: {resultado_da_branch}")
            
            resultados_finais.append(resultado_da_branch)

            if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                branch_anterior = nome_da_branch_atual
                print(f"Branch '{nome_da_branch_atual}' será usada como base para o próximo grupo.")
            
            print("-" * 60)
        
        print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas: {len(resultados_finais)} resultados")
        for i, resultado in enumerate(resultados_finais):
            print(f"[DEBUG]   Resultado {i+1}: success={resultado.get('success')}, pr_url={resultado.get('pr_url')}, message={resultado.get('message')}")
        
        return resultados_finais

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        error_result = [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]
        print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas (ERRO): {error_result}")
        return error_result
