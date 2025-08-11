# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO MAIS SEGURA E ROBUSTA)

from tools import github_connector
from .job_store import get_job, set_job
from github import GithubException

def processar_e_subir_mudancas_agrupadas(nome_repo: str, dados_agrupados: dict, job_id: str):
    """
    Processa os dados, cria branches e commita as mudanças usando apenas a API do GitHub (PyGithub).
    Agora lida com dados malformados da IA de forma segura.
    """
    try:
        repo = github_connector.connection(repositorio=nome_repo)
        branch_base = repo.get_branch(repo.default_branch)
        
        job_info = get_job(job_id)
        job_info['data']['commit_links'] = []
        set_job(job_id, job_info)

        print(f"[{job_id}] Iniciando processo de commit via API para {len(dados_agrupados.get('grupos', []))} grupo(s).")

        for grupo in dados_agrupados.get("grupos", []):
            branch_sugerida = grupo.get("branch_sugerida")
            if not branch_sugerida:
                print(f"[{job_id}] AVISO: Grupo ignorado por não ter 'branch_sugerida'.")
                continue

            titulo_commit_base = grupo.get("titulo_pr") or f"Refatoração automática para {branch_sugerida}"
            
            # --- 1. Criação da Branch (com verificação) ---
            try:
                print(f"[{job_id}] Verificando a existência da branch: {branch_sugerida}")
                repo.get_branch(branch_sugerida)
                print(f"[{job_id}] Branch '{branch_sugerida}' já existe. Usando-a.")
            except GithubException as e:
                if e.status == 404:
                    print(f"[{job_id}] Branch '{branch_sugerida}' não encontrada. Criando...")
                    repo.create_git_ref(ref=f'refs/heads/{branch_sugerida}', sha=branch_base.commit.sha)
                    print(f"[{job_id}] Branch '{branch_sugerida}' criada com sucesso.")
                else:
                    raise e

            # --- 2. Aplicação das Mudanças (arquivo por arquivo) ---
            commit_url_final = ""
            for i, mudanca in enumerate(grupo.get("conjunto_de_mudancas", [])):
                
                # [CORREÇÃO] Acessa as chaves de forma segura usando .get()
                caminho_arquivo = mudanca.get("caminho_do_arquivo")
                novo_conteudo = mudanca.get("novo_conteudo")

                # [CORREÇÃO] Verifica se os dados essenciais existem antes de prosseguir
                if not caminho_arquivo or novo_conteudo is None:
                    print(f"[{job_id}] AVISO: Mudança malformada ignorada. Faltando 'caminho_do_arquivo' ou 'novo_conteudo'. Dados: {mudanca}")
                    continue # Pula para a próxima mudança no loop

                titulo_commit_arquivo = f"{titulo_commit_base} (parte {i+1})"

                try:
                    arquivo = repo.get_contents(caminho_arquivo, ref=branch_sugerida)
                    print(f"[{job_id}] Atualizando arquivo '{caminho_arquivo}'...")
                    commit_result = repo.update_file(
                        path=caminho_arquivo,
                        message=titulo_commit_arquivo,
                        content=novo_conteudo,
                        sha=arquivo.sha,
                        branch=branch_sugerida
                    )
                    commit_url_final = commit_result['commit'].html_url
                    
                except GithubException as e:
                    if e.status == 404:
                        print(f"[{job_id}] Criando novo arquivo '{caminho_arquivo}'...")
                        commit_result = repo.create_file(
                            path=caminho_arquivo,
                            message=titulo_commit_arquivo,
                            content=novo_conteudo,
                            branch=branch_sugerida
                        )
                        commit_url_final = commit_result['commit'].html_url
                    else:
                        raise e

            # --- 3. Reportando o Link do Último Commit da Branch ---
            if commit_url_final:
                print(f"[{job_id}] Último commit na branch '{branch_sugerida}': {commit_url_final}")
                job_info = get_job(job_id)
                commit_info = {"branch": branch_sugerida, "url": commit_url_final}
                if 'commit_links' not in job_info['data']:
                    job_info['data']['commit_links'] = []
                job_info['data']['commit_links'].append(commit_info)
                set_job(job_id, job_info)
            else:
                 print(f"[{job_id}] Nenhum arquivo foi alterado para a branch '{branch_sugerida}'.")

        return {"status": "sucesso", "message": "Todos os commits foram realizados."}

    except Exception as e:
        print(f"ERRO FATAL ao processar commits via API para o repo {nome_repo}: {e}")
        job_info = get_job(job_id)
        if job_info:
            job_info['error'] = f"Falha durante o commit via API: {e}"
            job_info['status'] = 'failed'
            set_job(job_id, job_info)
        raise e
