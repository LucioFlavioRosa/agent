from typing import Dict, Any, List
from .github_committer import processar_branch_github
from .gitlab_committer import processar_branch_gitlab
from .azure_committer import processar_branch_azure
from .branch_name_sanitizer import BranchNameSanitizer
import json

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
    repository_type: str,
    modo_adicao_incremental: bool = False
) -> Dict[str, Any]:
    nome_branch_sanitizado = BranchNameSanitizer.sanitize(nome_branch)
    if repository_type == 'azure':
        print(f"[DEBUG] Usando repository_type explícito: Azure DevOps")
        resultado = processar_branch_azure(
            repo, nome_branch_sanitizado, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas,
            modo_adicao_incremental=modo_adicao_incremental
        )
        print(f"[DEBUG][orchestrator] Resultado Azure: {json.dumps(resultado, default=str)}")
    elif repository_type == 'gitlab':
        print(f"[DEBUG] Usando repository_type explícito: GitLab")
        resultado = processar_branch_gitlab(
            repo, nome_branch_sanitizado, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas,
            modo_adicao_incremental=modo_adicao_incremental
        )
        print(f"[DEBUG][orchestrator] Resultado GitLab: {json.dumps(resultado, default=str)}")
    else:
        print(f"[DEBUG] Usando repository_type explícito: GitHub")
        resultado = processar_branch_github(
            repo, nome_branch_sanitizado, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas,
            modo_adicao_incremental=modo_adicao_incremental
        )
        print(f"[DEBUG][orchestrator] Resultado GitHub: {json.dumps(resultado, default=str)}")
    # Validação obrigatória das chaves
    for chave in ["branch_name", "success", "pr_url"]:
        if chave not in resultado:
            raise Exception(f"[orchestrator] Resultado do committer não contém a chave obrigatória '{chave}': {json.dumps(resultado, default=str)}")
    return resultado
