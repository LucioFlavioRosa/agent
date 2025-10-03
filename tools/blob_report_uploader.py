from typing import Optional
import os

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> str:
    if usuario_executor:
        blob_path = f"{projeto}/{usuario_executor}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    else:
        blob_path = f"{projeto}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    # Aqui você deve implementar a lógica de upload real para o Blob Storage
    # Por exemplo, usando Azure Blob Storage SDK, boto3, etc.
    # O exemplo abaixo é apenas ilustrativo e deve ser adaptado conforme o backend real:
    os.makedirs(os.path.dirname(blob_path), exist_ok=True)
    with open(blob_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    # Retorne a URL ou caminho do blob salvo
    return blob_path
