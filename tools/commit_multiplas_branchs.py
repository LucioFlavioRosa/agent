# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO FINAL E CORRIGIDA COM FLUXO DE COMMIT DIRETO PARA REPOS NOVOS)

import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector # Corrigido para importar a classe
from typing import Dict, Any, List

def _processar_commit_direto(repo, conjunto_de_mudancas: list) -> Dict[str, Any]:
    """
    Realiza commits diretamente na branch main para repositórios novos.
    """
    resultado = {
        "branch_name": "main",
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0
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
                arquivo_existente = repo.get_contents(caminho, ref="main")
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch="main")
                else:
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch="main")
                commits_realizados += 1
                resultado["arquivos_modificados"].append(caminho)
            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch="main")
                commits_realizados += 1
                resultado["arquivos_modificados"].append(caminho)
            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch="main")
                commits_realizados += 1
                resultado["arquivos_modificados"].append(caminho)
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")
        except GithubException as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
    if commits_realizados > 0:
        resultado.update({
            "success": True,
            "message": "Commit direto realizado na branch main (repositório novo). Nenhum PR foi criado."
        })
    else:
        resultado.update({
            "success": True,
            "message": "Nenhuma mudança para commitar (commit direto em repo novo)."
        })
    return resultado


def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados: dict,
    base_branch: str = "main"
) -> List[Dict[str, Any]]:
    """
    Função principal que orquestra a criação de múltiplas branches e PRs.
    Se o repositório for novo, faz commit direto na main.
    """
    resultados_finais = []
    try:
        print("--- Iniciando o Processo de Pull Requests Empilhados OU Commit Direto ---")
        repo, repo_info = GitHubConnector.connection_with_info(repositorio=nome_repo)
        is_novo_repo = repo_info.get("is_novo_repo", False)
        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            return []
        # Fluxo alternativo para repositório novo
        if is_novo_repo:
            print("[COMMIT DIRETO] Detectado repositório novo. Realizando commit direto na branch main.")
            # Junta todas as mudanças de todos os grupos
            todas_mudancas = []
            for grupo_atual in lista_de_grupos:
                todas_mudancas.extend(grupo_atual.get("conjunto_de_mudancas", []))
            resultado_commit = _processar_commit_direto(repo, todas_mudancas)
            resultados_finais.append(resultado_commit)
            return resultados_finais
        # Fluxo tradicional para repositórios já existentes
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
            print("-" * 60)
        return resultados_finais
    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]

# Mantém _processar_uma_branch inalterado
