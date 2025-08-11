# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO FINAL E ROBUSTA - 100% API)

from . import github_connector
from .job_store import get_job, set_job
from github import GithubException

def processar_e_subir_mudancas_agrupadas(nome_repo: str, dados_agrupados: dict, job_id: str):
    """
    Cria uma cadeia de branches dependentes e abre um Pull Request para cada uma,
    usando exclusivamente a API do GitHub (PyGithub) de forma robusta.
    """
    try:
        repo = github_connector.connection(repositorio=nome_repo)
        
        branch_anterior_obj = repo.get_branch(repo.default_branch)
        branch_anterior_nome = repo.default_branch

        job_info = get_job(job_id)
        job_info['data']['commit_links'] = []
        set_job(job_id, job_info)

        print(f"[{job_id}] Iniciando processo de commit via API para {len(dados_agrupados.get('grupos', []))} grupo(s).")

        for grupo in dados_agrupados.get("grupos", []):
            branch_sugerida = grupo.get("branch_sugerida")
            mudancas = grupo.get("conjunto_de_mudancas", [])

            # --- 1. [NOVO] Verificação Prévia ---
            # Se não houver nome de branch ou nenhuma mudança, pula este grupo.
            if not branch_sugerida:
                print(f"[{job_id}] AVISO: Grupo ignorado por não ter 'branch_sugerida'.")
                continue
            if not mudancas:
                print(f"[{job_id}] INFO: Nenhum arquivo para alterar na branch '{branch_sugerida}'. Pulando.")
                continue

            titulo_pr = grupo.get("titulo_pr") or f"Refatoração automática para {branch_sugerida}"
            corpo_pr = grupo.get("resumo_do_pr") or "Pull request gerado automaticamente pelo MCP Agent."
            
            # --- 2. Criação da Branch a partir da anterior ---
            print(f"[{job_id}] Criando branch '{branch_sugerida}' a partir de '{branch_anterior_nome}'...")
            try:
                repo.create_git_ref(ref=f'refs/heads/{branch_sugerida}', sha=branch_anterior_obj.commit.sha)
                print(f"[{job_id}] Branch '{branch_sugerida}' criada com sucesso.")
            except GithubException as e:
                if e.status == 422 and "Reference already exists" in str(e.data):
                     print(f"[{job_id}] AVISO: Branch '{branch_sugerida}' já existe. Usando-a.")
                else:
                    raise e # Lança outros erros

            # --- 3. Aplicação das Mudanças (arquivo por arquivo) ---
            houve_commit = False
            for i, mudanca in enumerate(mudancas):
                caminho_arquivo = mudanca.get("caminho_do_arquivo")
                novo_conteudo = mudanca.get("novo_conteudo")

                if not caminho_arquivo or novo_conteudo is None:
                    print(f"[{job_id}] INFO: Mudança malformada para '{caminho_arquivo}'. Pulando.")
                    continue

                titulo_commit_arquivo = f"{titulo_pr} (parte {i+1})"

                try:
                    arquivo = repo.get_contents(caminho_arquivo, ref=branch_sugerida)
                    # Apenas atualiza se o conteúdo for realmente diferente
                    if arquivo.decoded_content.decode('utf-8') != novo_conteudo:
                        print(f"[{job_id}] Atualizando arquivo: {caminho_arquivo}")
                        repo.update_file(
                            path=caminho_arquivo, message=titulo_commit_arquivo,
                            content=novo_conteudo, sha=arquivo.sha, branch=branch_sugerida
                        )
                        houve_commit = True
                    else:
                        print(f"[{job_id}] INFO: Conteúdo de '{caminho_arquivo}' não mudou. Pulando commit.")

                except GithubException as e:
                    if e.status == 404: # Arquivo não existe, então o criamos
                        print(f"[{job_id}] Criando arquivo: {caminho_arquivo}")
                        repo.create_file(
                            path=caminho_arquivo, message=titulo_commit_arquivo,
                            content=novo_conteudo, branch=branch_sugerida
                        )
                        houve_commit = True
                    else:
                        raise e

            # --- 4. Cria o Pull Request se alguma mudança foi realmente comitada ---
            if houve_commit:
                print(f"[{job_id}] Pelo menos um commit foi feito. Criando Pull Request para a branch '{branch_sugerida}'...")
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
            else:
                print(f"[{job_id}] Nenhuma mudança real de conteúdo foi detectada para a branch '{branch_sugerida}'. Nenhum PR será criado.")
            
            # --- 5. Prepara para a próxima iteração ---
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
