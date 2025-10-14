import re

def build_report_blob_path(projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str) -> str:
    def sanitize_path_component(component: str) -> str:
        if not component:
            return "unknown"
        
        sanitized = re.sub(r'[<>:"|?*\\]', '_', component)
        sanitized = re.sub(r'/+', '_', sanitized)
        sanitized = sanitized.strip('.')
        
        return sanitized if sanitized else "unknown"
    
    projeto_clean = sanitize_path_component(projeto)
    analysis_type_clean = sanitize_path_component(analysis_type)
    repository_type_clean = sanitize_path_component(repository_type)
    repo_name_clean = sanitize_path_component(repo_name)
    branch_name_clean = sanitize_path_component(branch_name)
    analysis_name_clean = sanitize_path_component(analysis_name)
    
    return f"{projeto_clean}/{analysis_type_clean}/{repository_type_clean}/{repo_name_clean}/{branch_name_clean}/{analysis_name_clean}.md"