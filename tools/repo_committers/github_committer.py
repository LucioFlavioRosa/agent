from github import GithubException, UnknownObjectException
from typing import Dict, Any, List

def processar_branch_github(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
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