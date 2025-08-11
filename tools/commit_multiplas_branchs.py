# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO CORRIGIDA E FINAL)

import subprocess
import tempfile
import os

from . import github_connector
from .job_store import get_job, set_job

def run_command(command, working_dir):
    """Executa um comando de terminal e lida com erros."""
    print(f"Executando comando: {' '.join(command)} em {working_dir}")
    result = subprocess.run(command, cwd=working_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print("--- ERRO NO COMANDO GIT ---")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("---------------------------")
        raise RuntimeError(f"Falha no comando Git: {result.stderr}")
    return result.stdout

def processar_e_subir_mudancas_agrupadas(nome_repo: str, dados_agrupados: dict, job_id: str):
    """
    Cria uma cadeia de branches dependentes e abre um Pull Request para cada uma.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Obtém o objeto do repo E o token da nova função
            print(f"[{job_id}] Conectando ao GitHub e obtendo token...")
            repo_obj, token = github_connector.get_repo_and_token(repositorio=nome_repo)
            
            repo_url_with_auth = f"https://{token}@github.com/{nome_repo}.git"
            
            print(f"[{job_id}] Clonando repositório para diretório temporário...")
            run_command(["git", "clone", repo_url_with_auth, "."], working_dir=temp_dir)

            run_command(["git", "config", "user.name", "MCP Agent"], working_dir=temp_dir)
            run_command(["git", "config", "user.email", "mcp-agent@example.com"], working_dir=temp_dir)

            branch_anterior = repo_obj.default_branch

            job_info = get_job(job_id)
            job_info['data']['commit_links'] = []
            set_job(job_id, job_info)

            for grupo in dados_agrupados.get("grupos", []):
                branch_sugerida = grupo["branch_sugerida"]
                titulo_pr = grupo.get("titulo_pr") or f"Refatoração automática para {branch_sugerida}"
                corpo_pr = grupo.get("resumo_do_pr") or "Pull request gerado automaticamente pelo MCP Agent."

                print(f"[{job_id}] Criando branch '{branch_sugerida}' a partir de '{branch_anterior}'")
                run_command(["git", "checkout", branch_anterior], working_dir=temp_dir)
                run_command(["git", "pull"], working_dir=temp_dir)
                run_command(["git", "checkout", "-b", branch_sugerida], working_dir=temp_dir)
                
                for mudanca in grupo.get("conjunto_de_mudancas", []):
                    caminho_arquivo = os.path.join(temp_dir, mudanca["caminho_do_arquivo"])
                    novo_conteudo = mudanca.get("novo_conteudo")
                    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
                    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                        f.write(novo_conteudo)

                run_command(["git", "add", "."], working_dir=temp_dir)
                
                status_output = run_command(["git", "status", "--porcelain"], working_dir=temp_dir)
                if not status_output:
                    print(f"[{job_id}] Nenhum arquivo alterado na branch '{branch_sugerida}'. Pulando para a próxima.")
                    branch_anterior = branch_sugerida
                    continue

                run_command(["git", "commit", "-m", titulo_pr], working_dir=temp_dir)
                run_command(["git", "push", "-u", "origin", branch_sugerida], working_dir=temp_dir)
                
                print(f"[{job_id}] Criando Pull Request para a branch '{branch_sugerida}'...")
                try:
                    pr = repo_obj.create_pull(
                        title=titulo_pr,
                        body=corpo_pr,
                        head=branch_sugerida,
                        base=repo_obj.default_branch
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
                
                branch_anterior = branch_sugerida

            return {"status": "sucesso", "message": "Todos os Pull Requests foram processados."}

        except Exception as e:
            print(f"ERRO FATAL ao processar commits e PRs: {e}")
            job_info = get_job(job_id)
            if job_info:
                job_info['error'] = f"Falha durante a criação do PR: {e}"
                job_info['status'] = 'failed'
                set_job(job_id, job_info)
            raise e
