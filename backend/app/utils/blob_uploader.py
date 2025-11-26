import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import UploadFile, HTTPException
from typing import Optional

# Carrega a connection string do ambiente
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "arquivos")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

def upload_docx_to_blob(file: UploadFile, usuario_executor: str, projeto: str, analysis_name: str) -> str:
    """
    Faz upload do arquivo docx para o Azure Blob Storage no caminho correto e retorna a URL pública do blob.
    """
    try:
        blob_path = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx"
        blob_client = container_client.get_blob_client(blob_path)
        file.file.seek(0)
        blob_client.upload_blob(
            file.file,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
        blob_url = blob_client.url
        return blob_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload do arquivo para o Blob Storage: {str(e)}")
