from typing import Optional

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> str:
    if usuario_executor:
        blob_path = f"{projeto}/{usuario_executor}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    else:
        blob_path = f"{projeto}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    # Aqui você deve inserir a lógica real de upload para o blob storage, por exemplo usando Azure Blob Storage SDK ou outro serviço.
    # O código abaixo é um placeholder para ilustrar a assinatura e o caminho:
    # blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    # blob_client.upload_blob(report_text, overwrite=True)
    print(f"Salvando relatório em: {blob_path}")
    # Retorne a URL ou caminho do blob salvo
    return f"https://blobstorage.example.com/{blob_path}"
