from typing import Optional
import os

def read_report_from_blob(projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> Optional[str]:
    if usuario_executor:
        blob_path = f"{projeto}/{usuario_executor}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    else:
        blob_path = f"{projeto}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    if not os.path.exists(blob_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {blob_path}")
    with open(blob_path, 'r', encoding='utf-8') as f:
        return f.read()
