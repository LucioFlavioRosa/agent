def build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
    safe_project = (projeto or "sem_projeto").replace("/", "-").replace(" ", "_")
    safe_analysis_type = (analysis_type or "sem_tipo").replace("/", "-").replace(" ", "_")
    safe_repository_type = (repository_type or "sem_repo_type").replace("/", "-").replace(" ", "_")
    safe_repo_name = (repo_name or "sem_repo").replace("/", "-").replace(" ", "_")
    safe_branch_name = (branch_name or "main").replace("/", "-").replace(" ", "_")
    safe_analysis_name = (analysis_name or "sem_nome").replace("/", "-").replace(" ", "_")
    return f"reports/{safe_project}/{safe_analysis_type}/{safe_repository_type}/{safe_repo_name}/{safe_branch_name}/{safe_analysis_name}.md"