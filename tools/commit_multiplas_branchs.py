# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO FINAL E ROBUSTA)

import subprocess
import tempfile
import shutil
import os
import re

# [ALTERADO] Importa a nova função para pegar o token
from tools import github_connector
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
    Clona o repositório, cria branches, aplica mudanças, faz um commit por branch,
    e reporta o progresso de cada commit de volta para o job no Redis.
    """
    # Cria um diretório temporário que será limpo automaticamente no final
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # --- 1. Clona o repositório usando o token para autenticação ---
            print(f"[{job_id}] Obtendo token de autenticação...")
            token = github_connector.get_github_token()
            
            repo_url_with_auth = f"https://{token}@github.com/{nome_repo}.git"
            print(f"[{job_id}] Clonando repositório para diretório temporário...")
            run_command(["git", "clone", repo_url_with_auth, "."], working_dir=temp_dir)

            # Configura o usuário do git para este repositório
            run_command(["git", "config", "user.name", "MCP Agent"], working_dir=temp_dir)
            run_command(["git", "config", "user.email", "mcp-agent@example.com"], working_dir=temp_dir)

            job_info = get_job(job_id)
            job_info['data']['commit_links'] = []
            set_job(job_id, job_info)

            branch_base = "main" # Assumindo 'main', pode ser pego dinamicamente se necessário

            for grupo in dados_agrupados.get("grupos", []):
                branch_sugerida = grupo["branch_sugerida"]
                titulo_commit = grupo["titulo_pr"] or f"Refatoração automática para {branch_sugerida}"

                # --- 2. Cria a branch local e aplica as mudanças ---
                print(f"[{job_id}] Criando e trocando para a branch: {branch_sugerida}")
                run_command(["git", "checkout", "-b", branch_sugerida, f"origin/{branch_base}"], working_dir=temp_dir)
                
                for mudanca in grupo.get("conjunto_de_mudancas", []):
                    caminho_arquivo = os.path.join(temp_dir, mudanca["caminho_do_arquivo"])
                    novo_conteudo = mudanca["novo_conteudo"]
                    
                    # Garante que o diretório do arquivo existe
                    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
                    
                    print(f"[{job_id}] Escrevendo mudanças no arquivo: {caminho_arquivo}")
                    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                        f.write(novo_conteudo)

                # --- 3. Faz um único commit com todas as mudanças do grupo ---
                print(f"[{job_id}] Adicionando todos os arquivos modificados ao stage...")
                run_command(["git", "add", "."], working_dir=temp_dir)

                print(f"[{job_id}] Fazendo commit na branch '{branch_sugerida}'...")
                run_command(["git", "commit", "-m", titulo_commit], working_dir=temp_dir)
                
                # --- 4. Empurra (push) a nova branch para o repositório remoto ---
                print(f"[{job_id}] Enviando a branch '{branch_sugerida}' para o GitHub...")
                run_command(["git", "push", "-u", "origin", branch_sugerida], working_dir=temp_dir)
                
                # --- 5. Obtém o SHA do último commit e constrói a URL ---
                commit_sha = run_command(["git", "rev-parse", "HEAD"], working_dir=temp_dir).strip()
                commit_url = f"https://github.com/{nome_repo}/commit/{commit_sha}"

                print(f"[{job_id}] Commit realizado com sucesso! URL: {commit_url}")

                # Reporta o progresso para o Redis
                job_info = get_job(job_id)
                commit_info = {"branch": branch_sugerida, "url": commit_url}
                job_info['data']['commit_links'].append(commit_info)
                set_job(job_id, job_info)

                # Volta para a branch principal para o próximo loop
                run_command(["git", "checkout", branch_base], working_dir=temp_dir)

            return {"status": "sucesso", "message": "Todos os commits foram realizados."}

        except Exception as e:
            print(f"ERRO FATAL ao processar commits: {e}")
            job_info = get_job(job_id)
            if job_info:
                job_info['error'] = f"Falha durante o commit: {e}"
                job_info['status'] = 'failed'
                set_job(job_id, job_info)
            raise e
