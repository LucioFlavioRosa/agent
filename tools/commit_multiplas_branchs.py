# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO REFATORADA SEGUINDO SOLID)

import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from typing import Dict, Any, List, Optional

def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
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

        print(f"  [DEBUG] Processando arquivo: {caminho} com status: {status}")
        print(f"  [DEBUG] Conteúdo presente: {'Sim' if conteudo else 'Não'}")
        print(f"  [DEBUG] Tamanho do conteúdo: {len(str(conteudo)) if conteudo else 0} caracteres")

        try:
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
                print(f"  [DEBUG] Arquivo '{caminho}' já existe na branch (SHA: {sha_arquivo_existente[:8]}...)")
            except UnknownObjectException:
                print(f"  [DEBUG] Arquivo '{caminho}' não existe na branch - será criado")
                pass
            
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    if conteudo is not None:
                        repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                        commits_realizados += 1
                        resultado_branch["arquivos_modificados"].append(caminho)
                        print(f"  [SUCESSO] {caminho} atualizado (era ADICIONADO mas já existia)")
                    else:
                        print(f"  [ERRO] Arquivo '{caminho}' não tem conteúdo para atualização. Ignorando.")
                else:
                    if conteudo is not None:
                        repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                        commits_realizados += 1
                        resultado_branch["arquivos_modificados"].append(caminho)
                        print(f"  [SUCESSO] {caminho} criado")
                    else:
                        print(f"  [ERRO] Arquivo '{caminho}' não tem conteúdo para criação. Ignorando.")

            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                    
                if conteudo is not None:
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)
                    print(f"  [SUCESSO] {caminho} modificado")
                else:
                    print(f"  [ERRO] Arquivo '{caminho}' não tem conteúdo para modificação. Ignorando.")

            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                    
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
                print(f"  [SUCESSO] {caminho} removido")
            
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except GithubException as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
            
    print(f"\n[RESUMO] Commits realizados: {commits_realizados} de {len(conjunto_de_mudancas)} mudanças processadas")
    
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
        
        if repository_provider is None:
            repository_provider = GitHubRepositoryProvider()
            print("AVISO: Nenhum provedor especificado. Usando GitHubRepositoryProvider como padrão.")
        
        connector = GitHubConnector(repository_provider=repository_provider)
        repo = connector.connection(repositorio=nome_repo)

        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        print(f"[DEBUG] Dados agrupados recebidos: {json.dumps(dados_agrupados, indent=2, ensure_ascii=False)[:500]}...")
        print(f"[DEBUG] Total de grupos encontrados: {len(lista_de_grupos)}")
        
        if not lista_de_grupos:
            print("AVISO: Nenhum grupo de mudanças encontrado para processar.")
            print(f"[DEBUG] Estrutura dos dados recebidos: {list(dados_agrupados.keys())}")
            return []

        for i, grupo_atual in enumerate(lista_de_grupos):
            print(f"\n[DEBUG] Processando grupo {i+1}/{len(lista_de_grupos)}")
            print(f"[DEBUG] Estrutura do grupo: {list(grupo_atual.keys()) if isinstance(grupo_atual, dict) else 'Não é dict'}")
            
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            print(f"[DEBUG] Branch: {nome_da_branch_atual}")
            print(f"[DEBUG] Conjunto de mudanças: {len(conjunto_de_mudancas)} itens")
            
            if conjunto_de_mudancas:
                print(f"[DEBUG] Primeira mudança: {conjunto_de_mudancas[0] if conjunto_de_mudancas else 'Nenhuma'}")

            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                continue

            print(f"[INFO] Processando branch '{nome_da_branch_atual}' com {len(conjunto_de_mudancas)} mudanças")
            
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
        
        print(f"\n[RESUMO FINAL] Processados {len(resultados_finais)} grupos")
        for i, resultado in enumerate(resultados_finais):
            print(f"  Grupo {i+1}: {resultado['branch_name']} - {'SUCESSO' if resultado['success'] else 'FALHA'} - {resultado['message']}")
        
        return resultados_finais

    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]