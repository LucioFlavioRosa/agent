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
    conjunto_de_mudancas: list,
    repository_type: str
) -> Dict[str, Any]:
    if repository_type == 'azure':
        print(f"[DEBUG] Usando repository_type explícito: Azure DevOps")
        return processar_branch_azure(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    if repository_type == 'gitlab':
        print(f"[DEBUG] Usando repository_type explícito: GitLab")
        return processar_branch_gitlab(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    print(f"[DEBUG] Usando repository_type explícito: GitHub")
    return processar_branch_github(
        repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
        mensagem_pr, descricao_pr, conjunto_de_mudancas
    )