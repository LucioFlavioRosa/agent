# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO 100% API-PURA)

from . import github_connector
from .job_store import get_job, set_job
from github import GithubException

def processar_e_subir_mudancas_agrupadas(nome_repo: str, dados_agrupados: dict, job_id: str):
    """
    Cria uma cadeia de branches dependentes e abre um Pull Request para cada uma,
    usando exclusivamente a API do GitHub (PyGithub).
    """
    try:
        # [ALTERADO] Usa a função de conexão original
        repo = github_connector.connection(repositorio=nome_repo)
        
        # [ALTERADO] A branch base agora é obtida diretamente do objeto repo
        branch_anterior_obj = repo.get_branch(repo.default_branch)
        branch_anterior_nome = repo.default_branch

        job_info = get_job(job_id)
        job_info['data']['commit_links'] = []
        set_job(job_id, job_info)

        print(f"[{job_id}] Iniciando processo de commit via API para {len(dados_agrupados.get('grupos', []))} grupo(s).")

        for grupo in dados_agrupados.get("grupos", []):
            branch_sugerida = grupo.get("branch_sugerida")
            if not branch_sugerida:
                print(f"[{job_id}] AVISO: Grupo ignorado por não ter 'branch_sugerida'.")
                continue

            titulo_pr = grupo.get("titulo_pr") or f"Refatoração automática para {branch_sugerida}"
            corpo_pr = grupo.get("resumo_do_pr") or "Pull request gerado automaticamente pelo MCP Agent."
            
            # --- 1. Criação da Branch a partir da anterior ---
            print(f"[{job_id}] Criando branch '{branch_sugerida}' a partir de '{branch_anterior_nome}'...")
            try:
                # Tenta criar a branch. O SHA da branch anterior é o ponto de partida.
                repo.create_git_ref(ref=f'refs/heads/{branch_sugerida}', sha=branch_anterior_obj.commit.sha)
                print(f"[{job_id}] Branch '{branch_sugerida}' criada com sucesso.")
            except GithubException as e:
                # Código 422 significa que a branch já existe, o que é ok.
                if e.status == 422 and "Reference already exists" in str(e.data):
                     print(f"[{job_id}] AVISO: Branch '{branch_sugerida}' já existe. Usando-a.")
                else:
                    raise e # Lança outros erros

            # --- 2. Aplicação das Mudanças (arquivo por arquivo, um commit por arquivo) ---
            commit_url_final = ""
            for i, mudanca in enumerate(grupo.get("conjunto_de_mudancas", [])):
                caminho_arquivo = mudanca.get("caminho_do_arquivo")
                novo_conteudo = mudanca.get("novo_conteudo")

                if not caminho_arquivo or novo_conteudo is None:
                    print(f"[{job_id}] INFO: Nenhuma mudança necessária para o arquivo '{caminho_arquivo}'. Pulando.")
                    continue

                titulo_commit_arquivo = f"{titulo_pr} (parte {i+1})"

                try:
                    arquivo = repo.get_contents(caminho_arquivo, ref=branch_sugerida)
                    commit_result = repo.update_file(
                        path=caminho_arquivo, message=titulo_commit_arquivo,
                        content=novo_conteudo, sha=arquivo.sha, branch=branch_sugerida
                    )
                    commit_url_final = commit_result['commit'].html_url
                except GithubException as e:
                    if e.status == 404: # Arquivo não existe, então o criamos
                        commit_result = repo.create_file(
                            path=caminho_arquivo, message=titulo_commit_arquivo,
                            content=novo_conteudo, branch=branch_sugerida
                        )
                        commit_url_final = commit_result['commit'].html_url
                    else:
                        raise e

            # --- 3. Cria o Pull Request ---
            if commit_url_final: # Apenas cria PR se houve algum commit
                print(f"[{job_id}] Criando Pull Request para a branch '{branch_sugerida}'...")
                try:
                    pr = repo.create_pull(
                        title=titulo_pr, body=corpo_pr,
                        head=branch_sugerida, base=repo.default_branch
                    )
                    pr_url = pr.html_url
                    print(f"[{job_id}] Pull Request criado com sucesso! URL: {pr_url}")

                    job_info = get_job(job_id)
                    link_info = {"branch": branch_sugerida, "url": pr_url}
                    job_info['data']['commit_links'].append(link_info)
                    set_job(job_id, job_info)
                except Exception as pr_error:
                    if "A pull request already exists" in str(pr_error):
                        print(f"[{job_id}] AVISO: Um Pull Request para a branch '{branch_sugerida}' já existe.")
                    else:
                        raise pr_error
            
            # --- 4. Prepara para a próxima iteração ---
            branch_anterior_obj = repo.get_branch(branch_sugerida)
            branch_anterior_nome = branch_sugerida

        return {"status": "sucesso", "message": "Todos os Pull Requests foram processados."}

    except Exception as e:
        print(f"ERRO FATAL ao processar commits via API: {e}")
        job_info = get_job(job_id)
        if job_info:
            job_info['error'] = f"Falha durante a criação do PR via API: {e}"
            job_info['status'] = 'failed'
            set_job(job_id, job_info)
        raise e
