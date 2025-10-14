from typing import Dict, Any, List
import requests
import base64
import traceback
from tools.repo_committers.base_committer import BaseCommitter
from tools.conectores.azure_conector import AzureConector
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from tools.repo_committers.azure_pr_url_builder import build_pr_ui_url
from tools.repo_committers.path_normalizer import PathNormalizer
from tools.repo_committers.path_deduplicator import PathDeduplicator
import json
import random
import string

def _gerar_sufixo_aleatorio(tamanho=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=tamanho))

def _build_commit_ui_url(organization: str, project: str, repo_name: str, commit_id: str) -> str:
    return f"https://dev.azure.com/{organization}/{project}/_git/{repo_name}/commit/{commit_id}"

def processar_branch_azure(
    repo: Dict[str, Any],
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list,
    modo_adicao_incremental: bool = False
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote Azure DevOps para a Branch: '{nome_branch}' ---")
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    sanitized = BranchNameSanitizer.sanitize(nome_branch)
    if sanitized != nome_branch or sanitized == "invalid-branch":
        msg = f"Nome da branch inválido para Azure DevOps: '{nome_branch}' (sanitizado: '{sanitized}')"
        print(f"[ERRO][AZURE] {msg}")
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
        return resultado_branch
    try:
        BaseCommitter._validate_no_duplicate_paths(conjunto_de_mudancas)
    except ValueError as ve:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, str(ve))
        return resultado_branch
    mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
    if not mudancas_validas:
        raise ValueError(f"Tentativa de commit com conjunto de mudanças vazio. Verifique a saída do agente e a formatação dos dados. conjunto_de_mudancas={conjunto_de_mudancas}")
    try:
        organization = repo['_organization']
        project = repo['_project']
        repository_id = repo['id']
        repo_name = repo.get('name') or repo.get('_repository')
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
        print(f"[LOG][AZURE] Criando branch '{nome_branch}' a partir de '{branch_de_origem}'. Payload: {json.dumps(create_branch_payload)}")
        branch_response = requests.post(create_branch_url, headers=headers, json=create_branch_payload, timeout=30)
        print(f"[LOG][AZURE] branch_response.status_code: {branch_response.status_code}, branch_response.text: {branch_response.text}")
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
            print(f"[ERRO][AZURE] Erro ao criar branch: {branch_response.status_code} - {branch_response.text}")
            raise Exception(f"Erro ao criar branch: {branch_response.status_code} - {branch_response.text}")
        changes = []
        mudancas_filtradas = []
        for mudanca in mudancas_validas:
            caminho = mudanca.get("caminho")
            if not caminho:
                print(f"[WARN][AZURE] Mudança sem caminho válido detectada e ignorada: {mudanca}")
                continue
            mudancas_filtradas.append(mudanca)
        mudancas_validas = mudancas_filtradas
        for mudanca in mudancas_validas:
            if "caminho" in mudanca:
                mudanca["caminho"] = PathNormalizer.normalize(mudanca["caminho"])
        mudancas_validas = PathDeduplicator.deduplicate_changes(mudancas_validas)
        for mudanca in mudancas_validas:
            caminho = mudanca["caminho"]
            status = mudanca["status"]
            conteudo = mudanca["conteudo"]
            normalized_path = caminho
            change_item = {
                "item": {"path": normalized_path}
            }
            if status in ("ADICIONADO", "CRIAR", "CRIADO"):
                change_item["changeType"] = "add"
                change_item["newContent"] = {"content": conteudo or "", "contentType": "rawtext"}
            elif status == "MODIFICADO":
                if modo_adicao_incremental:
                    get_item_url = f"{base_url}/git/repositories/{repository_id}/items?path={normalized_path}&api-version=7.0"
                    item_response = requests.get(get_item_url, headers=headers, timeout=30)
                    if item_response.status_code == 200:
                        conteudo_existente = item_response.text
                        conteudo = BaseCommitter._mesclar_conteudo(conteudo_existente, conteudo)
                change_item["changeType"] = "edit"
                change_item["newContent"] = {"content": conteudo or "", "contentType": "rawtext"}
            elif status == "REMOVIDO":
                change_item["changeType"] = "delete"
            changes.append(change_item)
        if not changes:
            try:
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
            except ValueError as ve:
                print(f"[ERRO][AZURE] PR vazio mas pr_url inválido. Tentando retry com sufixo aleatório.")
                sufixo = _gerar_sufixo_aleatorio()
                novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                mensagem_pr = novo_titulo
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
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
        print(f"[LOG][AZURE] push_payload: {json.dumps(push_payload, indent=2, default=str)}")
        max_push_attempts = 2
        push_attempt = 0
        commit_url = None
        commit_id = None
        push_response = None
        while push_attempt < max_push_attempts:
            print(f"[LOG][AZURE] Realizando push tentativa {push_attempt+1} para branch '{nome_branch}' com current_commit_id: {current_commit_id}")
            push_response = requests.post(push_url, headers=headers, json=push_payload, timeout=60)
            print(f"[LOG][AZURE] push_response.status_code: {push_response.status_code}, push_response.text: {push_response.text}")
            if push_response.status_code in [200, 201]:
                push_data = push_response.json()
                if 'commits' not in push_data or not isinstance(push_data['commits'], list) or len(push_data['commits']) == 0:
                    print(f"[ERRO][AZURE] Push realizado mas resposta inválida: {json.dumps(push_data, default=str)}")
                    raise Exception(f"Push realizado mas resposta inválida: {json.dumps(push_data, default=str)}")
                try:
                    commit_info = push_data['commits'][0]
                    commit_id = commit_info.get('commitId')
                    if commit_id:
                        commit_url_candidate = _build_commit_ui_url(organization, project, repo_name, commit_id)
                        print(f"[LOG][AZURE] commit_id extraído: {commit_id}, commit_url_candidate: {commit_url_candidate}")
                        if BaseCommitter._validate_commit_url(commit_url_candidate):
                            commit_url = commit_url_candidate
                        else:
                            print(f"[WARN][AZURE] commit_url construído não é válido: {commit_url_candidate}")
                            commit_url = None
                except Exception as e:
                    print(f"[ERRO][AZURE] Não foi possível extrair commit_url do push_response: {e}")
                    commit_url = None
                break
            elif push_response.status_code in [400, 409]:
                print(f"[ERRO][AZURE] Push falhou com status {push_response.status_code}. Tentando atualizar current_commit_id e retentar...")
                refs_url_destino = f"{base_url}/git/repositories/{repository_id}/refs?filter=heads/{nome_branch}&api-version=7.0"
                refs_response_destino = requests.get(refs_url_destino, headers=headers, timeout=30)
                refs_response_destino.raise_for_status()
                refs_data_destino = refs_response_destino.json()
                if not refs_data_destino.get('value'):
                    raise Exception(f"Branch '{nome_branch}' não encontrada ao tentar atualizar SHA para retry do push.")
                current_commit_id = refs_data_destino['value'][0]['objectId']
                print(f"[DEBUG][AZURE] Novo current_commit_id para retry: {current_commit_id}")
                push_payload['refUpdates'][0]['oldObjectId'] = current_commit_id
                push_attempt += 1
                continue
            else:
                print(f"[ERRO][AZURE] Erro ao fazer push (commit): {push_response.status_code} - {push_response.text}")
                raise Exception(f"Erro ao fazer push (commit): {push_response.status_code} - {push_response.text}")
        if push_response is None or push_response.status_code not in [200, 201]:
            raise Exception(f"Falha crítica ao enviar alterações após {max_push_attempts} tentativas. Último erro: {push_response.status_code if push_response else 'SEM RESPOSTA'} - {push_response.text if push_response else ''}")
        if commit_url and BaseCommitter._validate_commit_url(commit_url):
            resultado_branch['commit_url'] = commit_url
        else:
            resultado_branch['commit_url'] = None
        tentativas = 0
        while tentativas < 2:
            try:
                print(f"[DEBUG][AZURE] Criando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'")
                pr_url = f"{base_url}/git/repositories/{repository_id}/pullrequests?api-version=7.0"
                pr_payload = {
                    "sourceRefName": f"refs/heads/{nome_branch}",
                    "targetRefName": f"refs/heads/{branch_alvo_do_pr}",
                    "title": mensagem_pr,
                    "description": descricao_pr
                }
                pr_response = requests.post(pr_url, headers=headers, json=pr_payload, timeout=30)
                print(f"[LOG][AZURE] pr_response.status_code: {pr_response.status_code}, pr_response.text: {pr_response.text}")
                if pr_response.status_code in [200, 201]:
                    pr_data = pr_response.json()
                    print(f"[DEBUG][AZURE] pr_response.status_code: {pr_response.status_code}")
                    print(f"[DEBUG][AZURE] pr_data COMPLETO: {json.dumps(pr_data, indent=2, default=str)}")
                    pull_request_id = pr_data.get('pullRequestId')
                    if pull_request_id and organization and project and repo_name:
                        pr_web_url = build_pr_ui_url(organization, project, repo_name, pull_request_id)
                        print(f"[DEBUG][AZURE] pr_web_url construído manualmente: {pr_web_url}")
                    else:
                        pr_web_url = None
                        print(f"[ERRO][AZURE] Não foi possível construir a URL de UI do PR: pullRequestId={pull_request_id}, organization={organization}, project={project}, repo_name={repo_name}")
                    if not pr_web_url or not isinstance(pr_web_url, str) or not pr_web_url.strip():
                        print(f"[ERRO][AZURE] pr_web_url extraído está vazio. pr_data: {pr_data}")
                        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"PR criado mas web_url inválido: {json.dumps(pr_data, default=str)}")
                        break
                    BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_web_url.strip())
                    break
                else:
                    if "already exists" in pr_response.text.lower():
                        print(f"AVISO: PR para esta branch Azure já existe.")
                        try:
                            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, message="PR já existente.")
                        except ValueError as ve:
                            print(f"[ERRO][AZURE] PR já existente mas pr_url inválido. Tentando retry com sufixo aleatório.")
                            sufixo = _gerar_sufixo_aleatorio()
                            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                            mensagem_pr = novo_titulo
                            tentativas += 1
                            continue
                        break
                    else:
                        print(f"[ERRO][AZURE] Erro ao criar PR Azure: {pr_response.status_code} - {pr_response.text}")
                        raise Exception(f"Erro ao criar PR Azure: {pr_response.status_code} - {pr_response.text}")
            except ValueError as ve:
                print(f"[ERRO][AZURE] PR retornado sem web_url ou web_url inválido.")
                if tentativas == 0:
                    sufixo = _gerar_sufixo_aleatorio()
                    novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                    print(f"[AZURE][RETRY] Tentando criar PR novamente com título modificado: {novo_titulo}")
                    mensagem_pr = novo_titulo
                    tentativas += 1
                    continue
                else:
                    raise
            except Exception as e:
                print(f"[ERRO][AZURE] Falha crítica ao criar PR: {e}")
                BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro crítico ao validar PR: {e}")
                break
    except Exception as e:
        print(f"[ERRO][AZURE] ERRO FATAL ao processar branch Azure '{nome_branch}': {type(e).__name__}: {e}")
        traceback.print_exc()
        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro fatal: {e}")
    print(f"[DEBUG][AZURE] Resultado final da branch {nome_branch}: {resultado_branch}")
    return resultado_branch
