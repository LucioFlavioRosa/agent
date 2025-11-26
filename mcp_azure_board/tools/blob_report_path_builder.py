def build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
    """
    Constrói o caminho do blob para um relatório, padronizado para o MCP Azure Board.
    """
    repo_segment = repo_name.replace('/', '_') if repo_name else 'repo'
    branch_segment = branch_name.replace('/', '_') if branch_name else 'branch'
    analysis_segment = analysis_name.replace('/', '_') if analysis_name else 'analysis'
    return f"{projeto}/{analysis_type}/{repository_type}/{repo_segment}/{branch_segment}/{analysis_segment}.md"
