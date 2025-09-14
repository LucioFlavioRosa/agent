from typing import Dict, Any, List
import requests
import base64
import traceback
from tools.repo_committers.base_committer import BaseCommitter
from tools.conectores.azure_conector import AzureConector

def processar_branch_azure(
    repo: Dict[str, Any],
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote Azure DevOps para a Branch: '{nome_branch}' ---")
    
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    
    try:
        organization = repo['_organization']
        project = repo['_project']
        repository_id = repo['id']

        connector = AzureConector.create_with_defaults()
        token = connector._get_token_for_org(organization, platform='azure')
        
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"
        }
        
        print(f"[DEBUG][AZURE] Obtendo referência da branch de origem: {branch_de_origem}")
        refs_url_origem = f"{base_url}/git/repositories/{repository_id}/refs?filter=heads/{branch_de_origem}&api-version=7.0"
        refs_response_origem = requests.get(refs_url_origem, headers=headers, timeout=30)
        refs_response_origem.raise_for_status()
        
        refs_data_origem = refs_response_origem.json()
        if not refs_data_origem.get('value'):
            raise Exception(f"Branch de origem '{branch_de_origem}' não encontrada")
        
        source_commit_id = refs_data_origem['value'][0]['objectId']
        print(f"[DEBUG][AZURE] Commit ID da branch origem: {source_commit_id}")

        current_commit_id = ""
        create_branch_url = f"{base_url}/git/repositories/{repository_id}/refs?api-version=7.0"
        create_branch_payload = [{
            "name": f"refs/heads/{nome_branch}",
            "oldObjectId": "0000000000000000000000000000000000000000",
            "newObjectId": source_commit_id
        }]
        
        branch_response = requests.post(create_branch_url, headers=headers, json=create_branch_payload, timeout=30)
        
        if branch_response.status_code in [200, 201]:
            print(f"SUCESSO: Branch '{nome_branch}' criada.")
            current_commit_id = source_commit_id
        elif "already exists" in branch_response.text.lower():
            print(f"AVISO: A branch '{nome_branch}' já existe. Buscando seu commit ID atual...")
            refs_url_destino = f"{base_url}/git/repositories/{repository_id}/refs?filter=heads/{nome_branch}&api-version=7.0"
            refs_response_destino = requests.get(refs_url_destino, headers=headers, timeout=30)
            refs_response_destino.raise_for_status()
            refs_data_destino = refs_response_destino.json()

            if not refs_data_destino.get('value'):
                raise Exception(f"Branch existente '{nome_branch}' não pôde ser encontrada para obter o commit ID.")
            
            current_commit_id = refs_data_destino['value'][0]['objectId']
            print(f"[DEBUG][AZURE] Commit ID da branch existente '{nome_branch}': {current_commit_id}")
        else:
            raise Exception(f"Erro ao criar branch: {branch_response.status_code} - {branch_response.text}")

        changes = []
        mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
        
        for mudanca in mudancas_validas:
            caminho = mudanca["caminho"]
            status = mudanca["status"]
            conteudo = mudanca["conteudo"]
                
            change_item = {
                "item": {"path": f"/{caminho}"}
            }
            
            if status in ("ADICIONADO", "CRIAR", "CRIADO"):
                change_item["changeType"] = "add"
                change_item["newContent"] = {"content": conteudo or "", "contentType": "rawtext"}
            elif status == "MODIFICADO":
                change_item["changeType"] = "edit"
                change_item["newContent"] = {"content": conteudo or "", "contentType": "rawtext"}
            elif status == "REMOVIDO":
                change_item["changeType"] = "delete"
            
            changes.append(change_item)
        
        if not changes:
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, message="Nenhuma mudança para commitar.")
            return resultado_branch
        
        print(f"[DEBUG][AZURE] Criando commit com {len(changes)} mudanças")
        push_url = f"{base_url}/git/repositories/{repository_id}/pushes?api-version=7.0"
        push_payload = {
            "refUpdates": [{
                "name": f"refs/heads/{nome_branch}",
                "oldObjectId": current_commit_id
            }],
            "commits": [{
                "comment": mensagem_pr,
                "changes": changes
            }]
        }
        
        push_response = requests.post(push_url, headers=headers, json=push_payload, timeout=60)
        if push_response.status_code not in [200, 201]:
            raise Exception(f"Erro ao fazer push (commit): {push_response.status_code} - {push_response.text}")
        
        print(f"[DEBUG][AZURE] Commit realizado com sucesso.")
        
        print(f"[DEBUG][AZURE] Criando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'")
        pr_url = f"{base_url}/git/repositories/{repository_id}/pullrequests?api-version=7.0"
        pr_payload = {
            "sourceRefName": f"refs/heads/{nome_branch}",
            "targetRefName": f"refs/heads/{branch_alvo_do_pr}",
            "title": mensagem_pr,
            "description": descricao_pr
        }
        
        pr_response = requests.post(pr_url, headers=headers, json=pr_payload, timeout=30)
        if pr_response.status_code in [200, 201]:
            pr_data = pr_response.json()
            pr_web_url = pr_data.get('_links', {}).get('web', {}).get('href', '')
            if not pr_web_url:
                 pr_web_url = f"https://dev.azure.com/{organization}/{project}/_git/{repo['name']}/pullrequest/{pr_data['pullRequestId']}"
            print(f"Pull Request Azure criado com sucesso! URL: {pr_web_url}")
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_web_url)
        else:
            if "already exists" in pr_response.text.lower():
                print(f"AVISO: PR para esta branch Azure já existe.")
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, message="PR já existente.")
            else:
                raise Exception(f"Erro ao criar PR Azure: {pr_response.status_code} - {pr_response.text}")
        
    except Exception as e:
        print(f"[ERRO][AZURE] ERRO FATAL ao processar branch Azure '{nome_branch}': {type(e).__name__}: {e}")
        traceback.print_exc()
        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro fatal: {e}")
    
    return resultado_branch
