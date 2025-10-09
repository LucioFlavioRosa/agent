from typing import Dict, Any
from tools.utils.retry_helper import retry_with_backoff
import logging

def processar_branch_azure(
    repo,
    nome_branch,
    branch_de_origem,
    branch_alvo_do_pr,
    mensagem_pr,
    descricao_pr,
    conjunto_de_mudancas,
    modo_adicao_incremental=False
) -> Dict[str, Any]:
    job_id = None
    if hasattr(repo, 'job_id'):
        job_id = repo.job_id
    arquivos_modificados = []
    def criar_branch_func():
        return repo.criar_branch(nome_branch, branch_de_origem)
    def fazer_commit_func():
        return repo.fazer_commit(nome_branch, conjunto_de_mudancas, modo_adicao_incremental=modo_adicao_incremental)
    def criar_pr_func():
        return repo.criar_pull_request(nome_branch, branch_alvo_do_pr, mensagem_pr, descricao_pr)
    try:
        retry_with_backoff(criar_branch_func, max_attempts=3, initial_delay=2, backoff_factor=2, exceptions=(Exception,), job_id=job_id, context_msg='criar_branch')
    except Exception as e:
        if 'TF401028' in str(e) or 'GitReferenceStaleException' in str(e):
            logging.error(f"[{job_id}] [AZURE_COMMITTER] Conflito de referência ao criar branch: {e}")
            return {
                "branch_name": nome_branch,
                "success": False,
                "pr_url": f"ERRO: Conflito de referência ao criar branch: {str(e)}",
                "message": str(e),
                "arquivos_modificados": []
            }
        logging.error(f"[{job_id}] [AZURE_COMMITTER] Erro ao criar branch: {e}")
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": f"ERRO: Falha ao criar branch: {str(e)}",
            "message": str(e),
            "arquivos_modificados": []
        }
    try:
        commit_result = retry_with_backoff(fazer_commit_func, max_attempts=3, initial_delay=2, backoff_factor=2, exceptions=(Exception,), job_id=job_id, context_msg='fazer_commit')
        arquivos_modificados = commit_result.get('arquivos_modificados', [])
    except Exception as e:
        if 'TF401028' in str(e) or 'GitReferenceStaleException' in str(e):
            logging.error(f"[{job_id}] [AZURE_COMMITTER] Conflito de referência ao fazer commit: {e}")
            return {
                "branch_name": nome_branch,
                "success": False,
                "pr_url": f"ERRO: Conflito de referência ao fazer commit: {str(e)}",
                "message": str(e),
                "arquivos_modificados": []
            }
        logging.error(f"[{job_id}] [AZURE_COMMITTER] Erro ao fazer commit: {e}")
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": f"ERRO: Falha ao fazer commit: {str(e)}",
            "message": str(e),
            "arquivos_modificados": []
        }
    try:
        pr_result = retry_with_backoff(criar_pr_func, max_attempts=3, initial_delay=2, backoff_factor=2, exceptions=(Exception,), job_id=job_id, context_msg='criar_pull_request')
        pr_url = pr_result.get('url') or pr_result.get('pr_url')
        return {
            "branch_name": nome_branch,
            "success": True,
            "pr_url": pr_url,
            "message": "PR criado.",
            "arquivos_modificados": arquivos_modificados
        }
    except Exception as e:
        if 'TF401028' in str(e) or 'GitReferenceStaleException' in str(e):
            logging.error(f"[{job_id}] [AZURE_COMMITTER] Conflito de referência ao criar PR: {e}")
            return {
                "branch_name": nome_branch,
                "success": False,
                "pr_url": f"ERRO: Conflito de referência ao criar PR: {str(e)}",
                "message": str(e),
                "arquivos_modificados": arquivos_modificados
            }
        logging.error(f"[{job_id}] [AZURE_COMMITTER] Erro ao criar PR: {e}")
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": f"ERRO: Falha ao criar PR: {str(e)}",
            "message": str(e),
            "arquivos_modificados": arquivos_modificados
        }
