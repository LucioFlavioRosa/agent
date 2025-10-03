from typing import Optional

def read_report_from_blob(projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> Optional[str]:
    from azure.storage.blob import BlobServiceClient
    import os
    connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER_NAME"]
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    usuario_executor_dir = usuario_executor if usuario_executor and usuario_executor.strip() else "usuario_desconhecido"
    blob_path = f"{projeto}/{usuario_executor_dir}/{analysis_type}/{repository_type}/{repo_name}/{branch_name}/{analysis_name}.md"
    print(f"[BlobReader] Lendo relatório de: {blob_path} (usuario_executor='{usuario_executor_dir}')")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    try:
        download_stream = blob_client.download_blob()
        return download_stream.readall().decode('utf-8')
    except Exception as e:
        print(f"[BlobReader] Erro ao ler blob: {e}")
        raise FileNotFoundError(f"Relatório não encontrado em {blob_path}")
