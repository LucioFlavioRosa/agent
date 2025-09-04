from typing import Dict, Any, List

def processar_branch_azure(
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
        
        from tools.conectores.azure_conector import AzureConector
        connector = AzureConector.create_with_defaults()
        token = connector._get_token_for_org(organization)
        
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