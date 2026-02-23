import logging
from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile
from backend.app.utils.blob_storage_helper import sanitize_email, build_blob_path

logger = logging.getLogger("mcp_blob_storage")

class BlobStorageService:
    @staticmethod
    async def upload_document(blob_conn_str: str, blob_container: str, company_id: str, email: str, project_id: str, job_id: str, file: UploadFile) -> str:
        """
        Faz upload de um documento para o Blob Storage no caminho:
        company_id/email_sanitizado/project_id/job_id/filename
        Retorna o caminho completo do blob salvo.
        """
        logger.info("[BlobStorageService] Iniciando upload de documento...")
        if not file:
            raise ValueError("Arquivo não fornecido para upload.")
        filename = file.filename
        blob_path = build_blob_path(company_id, email, project_id, job_id, filename)
        logger.info(f"[BlobStorageService] Caminho do blob: {blob_path}")

        async with BlobServiceClient.from_connection_string(blob_conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(blob_container)
            logger.info(f"[BlobStorageService] Verificando existência do container: {blob_container}")
            if not await container_client.exists():
                logger.info(f"[BlobStorageService] Container '{blob_container}' não existe. Criando...")
                await container_client.create_container()
            blob_client = container_client.get_blob_client(blob_path)
            conteudo = await file.read()
            logger.info(f"[BlobStorageService] Fazendo upload do arquivo '{filename}'...")
            await blob_client.upload_blob(conteudo, overwrite=True)
            logger.info(f"[BlobStorageService] Upload concluído: {blob_path}")
        return blob_path
