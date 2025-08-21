# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO FINAL E CORRIGIDA COM COMMIT DIRETO NA MAIN)

import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector # Corrigido para importar a classe
from typing import Dict, Any, List

def _commit_direto_main(repo, conjunto_de_mudancas: list) -> List[str]:
    """
    Realiza commit direto na branch main para repositórios novos.
    """
    arquivos_modificados = []
    branch_main = repo.default_branch
    print(f"Commit direto na branch '{branch_main}' (repositório novo).")
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
                arquivo_existente = repo.get_contents(caminho, ref=branch_main)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=branch_main)
                else:
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=branch_main)
                arquivos_modificados.append(caminho)
            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch main. Ignorando.")
                    continue
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=branch_main)
                arquivos_modificados.append(caminho)
            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=branch_main)
                arquivos_modificados.append(caminho)
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")
        except GithubException as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
    return arquivos_modificados

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
        "arquivos_modificados": [] # Adicionado para melhor feedback
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
                pass
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            elif status == "MODIFICADO":
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
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
    commit_direto_main: bool = False
) -> List[Dict[str, Any]]:
    """
    Função principal que orquestra a criação de múltiplas branches e PRs ou commit direto na main.
    """
    resultados_finais = []
    try:
        print("--- Iniciando o Processo de Pull Requests Empilhados ou Commit Direto na Main ---")
        repo_info = GitHubConnector.connection(nome_repo, return_info=True)
        if isinstance(repo_info, tuple):
            repo, repo_metadata = repo_info
        else:
            repo = repo_info
            repo_metadata = {}
        is_novo_repo = repo_metadata.get('is_novo_repo', False)
        # Se commit_direto_main for True OU o repo for novo, faz commit direto na main
        if commit_direto_main or is_novo_repo:
            print("[Commit] Fluxo de commit direto na main ativado.")
            lista_de_grupos = dados_agrupados.get("grupos", [])
            arquivos_modificados = []
            for grupo_atual in lista_de_grupos:
                conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])
                arquivos_modificados += _commit_direto_main(repo, conjunto_de_mudancas)
            resultados_finais.append({
                "branch_name": repo.default_branch,
                "success": True,
                "pr_url": None,
                "message": "Commit direto na main realizado.",
                "arquivos_modificados": arquivos_modificados
            })
            return resultados_finais
        # Fluxo tradicional
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
            print("-" * 60)
        return resultados_finais
    except Exception as e:
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]

# Testes unitários/mocks básicos para commit direto na main
if __name__ == "__main__":
    class MockRepo:
        def __init__(self):
            self.files = {}
            self.default_branch = "main"
        def get_contents(self, path, ref=None):
            if path in self.files:
                class File:
                    sha = "sha-mock"
                return File()
            raise UnknownObjectException(404, "Not found", None)
        def create_file(self, path, message, content, branch):
            self.files[path] = content
        def update_file(self, path, message, content, sha, branch):
            self.files[path] = content
        def delete_file(self, path, message, sha, branch):
            if path in self.files:
                del self.files[path]
    # Teste: commit direto na main
    repo = MockRepo()
    mudancas = [
        {"caminho_do_arquivo": "a.py", "status": "ADICIONADO", "conteudo": "print('a')"},
        {"caminho_do_arquivo": "b.py", "status": "MODIFICADO", "conteudo": "print('b')"},
        {"caminho_do_arquivo": "c.py", "status": "REMOVIDO", "conteudo": None}
    ]
    arquivos_modificados = _commit_direto_main(repo, mudancas)
    assert "a.py" in arquivos_modificados
    assert "b.py" in arquivos_modificados
    print("Teste de commit direto na main passou.")
