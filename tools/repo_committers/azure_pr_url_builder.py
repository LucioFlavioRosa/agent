def build_pr_ui_url(organization: str, project: str, repo_name: str, pr_id: int) -> str:
    if not isinstance(organization, str) or not organization:
        raise ValueError("organization deve ser uma string não vazia")
    if not isinstance(project, str) or not project:
        raise ValueError("project deve ser uma string não vazia")
    if not isinstance(repo_name, str) or not repo_name:
        raise ValueError("repo_name deve ser uma string não vazia")
    if not isinstance(pr_id, int) or pr_id <= 0:
        raise ValueError("pr_id deve ser um inteiro positivo")
    return f"https://dev.azure.com/{organization}/{project}/_git/{repo_name}/pullrequest/{pr_id}"
