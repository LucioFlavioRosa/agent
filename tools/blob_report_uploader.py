from typing import Optional
import os

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> str:
    if usuario_executor:
        blob_path = f"{projeto}/{usuario_executor}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    else:
        blob_path = f"{projeto}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    # Aqui você implementaria a lógica real de upload para o Blob Storage
    # Por exemplo, usando Azure Blob Storage SDK, boto3, etc.
    # O código abaixo é apenas um placeholder para simular o upload e retorno da URL
    # Salva localmente para simular o upload
    os.makedirs(os.path.dirname(blob_path), exist_ok=True)
    with open(blob_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    # Retorna o caminho como se fosse uma URL do blob
    return f"blob://{blob_path}"
