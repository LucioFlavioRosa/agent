from typing import Optional

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> str:
    from azure.storage.blob import BlobServiceClient
    import os
    connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER_NAME"]
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    usuario_executor_dir = usuario_executor if usuario_executor and usuario_executor.strip() else "usuario_desconhecido"
    blob_path = f"{projeto}/{usuario_executor_dir}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    print(f"[BlobUploader] Salvando relatório em: {blob_path} (usuario_executor='{usuario_executor_dir}')")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    blob_client.upload_blob(report_text, overwrite=True)
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_path}"
    return blob_url
