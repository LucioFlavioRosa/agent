from typing import Dict, Any, List
from .github_committer import processar_branch_github
from .gitlab_committer import processar_branch_gitlab
from .azure_committer import processar_branch_azure

def _is_gitlab_project(repo) -> bool:
    return hasattr(repo, 'web_url') or 'gitlab' in str(type(repo)).lower()

def _is_azure_repo(repo) -> bool:
    return hasattr(repo, '_provider_type') and repo._provider_type == 'azure_devops'

def processar_branch_por_provedor(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    if _is_azure_repo(repo):
        print(f"[DEBUG] Detectado repositório Azure DevOps, delegando para fluxo específico")
        return processar_branch_azure(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    if _is_gitlab_project(repo):
        print(f"[DEBUG] Detectado repositório GitLab, delegando para fluxo específico")
        return processar_branch_gitlab(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    print(f"[DEBUG] Detectado repositório GitHub, delegando para fluxo específico")
    return processar_branch_github(
        repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
        mensagem_pr, descricao_pr, conjunto_de_mudancas
    )