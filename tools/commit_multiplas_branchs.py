# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO ATUALIZADA)

from tools import github_connector
# [NOVO] Importa as funções para interagir com o Redis
from job_store import get_job, set_job

# [ALTERADO] A função agora recebe o job_id para poder reportar o progresso
def processar_e_subir_mudancas_agrupadas(nome_repo: str, dados_agrupados: dict, job_id: str):
    """
    Processa os dados, cria branches, commita as mudanças e reporta o progresso
    de cada commit de volta para o job no Redis.
    """
    try:
        repo = github_connector.connection(repositorio=nome_repo)
        branch_base = repo.get_branch(repo.default_branch)
        
        # [NOVO] Inicializa a lista de links de commit no Redis
        job_info = get_job(job_id)
        job_info['data']['commit_links'] = []
        set_job(job_id, job_info)

        for grupo in dados_agrupados.get("grupos", []):
            branch_sugerida = grupo["branch_sugerida"]
            titulo_pr = grupo["titulo_pr"]
            
            # Cria uma nova branch a partir da branch padrão
            print(f"[{job_id}] Criando branch: {branch_sugerida}")
            repo.create_git_ref(ref=f'refs/heads/{branch_sugerida}', sha=branch_base.commit.sha)

            actions = []
            for mudanca in grupo.get("conjunto_de_mudancas", []):
                caminho_arquivo = mudanca["caminho_do_arquivo"]
                novo_conteudo = mudanca["novo_conteudo"]
                
                # Prepara a ação de criar ou atualizar o arquivo
                try:
                    # Tenta obter o arquivo para saber se é uma atualização ou criação
                    arquivo_existente = repo.get_contents(caminho_arquivo, ref=branch_sugerida)
                    repo.update_file(
                        path=caminho_arquivo,
                        message=f"Refatora: {caminho_arquivo}",
                        content=novo_conteudo,
                        sha=arquivo_existente.sha,
                        branch=branch_sugerida
                    )
                except Exception: # Se o arquivo não existe, cria um novo
                    repo.create_file(
                        path=caminho_arquivo,
                        message=f"Cria: {caminho_arquivo}",
                        content=novo_conteudo,
                        branch=branch_sugerida
                    )

            # Após fazer as mudanças, pega o último commit da branch
            ultimo_commit = repo.get_branch(branch_sugerida).commit
            commit_sha = ultimo_commit.sha
            commit_url = ultimo_commit.html_url
            
            print(f"[{job_id}] Commit realizado na branch '{branch_sugerida}': {commit_url}")

            # [NOVO] Reporta o progresso para o Redis
            job_info = get_job(job_id)
            commit_info = {"branch": branch_sugerida, "url": commit_url}
            job_info['data']['commit_links'].append(commit_info)
            set_job(job_id, job_info)
            
        return {"status": "sucesso", "message": "Todos os commits foram realizados."}

    except Exception as e:
        print(f"ERRO ao processar commits para o repo {nome_repo}: {e}")
        # Reporta o erro para o Redis
        job_info = get_job(job_id)
        job_info['error'] = f"Falha durante o commit: {e}"
        job_info['status'] = 'failed'
        set_job(job_id, job_info)
        raise e
