import logging
from typing import Optional
from azure.storage.blob.aio import BlobServiceClient
from backend.app.services.vault_service import vault_service

logger = logging.getLogger("mcp_blob_storage")

class BlobStorageService:
    async def save_document(
        self,
        company_id: str,
        project_id: str,
        job_id: str,
        file_content: bytes,
        filename: str,
        group_id: Optional[str] = None
    ) -> str:
        """
        Salva um documento no Azure Blob Storage seguindo o caminho:
        company_id/project_id/job_id/filename
        - O nome do container é company_id.
        - A connection string é obtida do Key Vault via vault_service.get_secret.
        - Cria o container se não existir.
        - Retorna o caminho completo do blob.
        """
        blob_path = f"{project_id}/{job_id}/{filename}"
        full_blob_path = f"{company_id}/{blob_path}"
        try:
            logger.info(f"[BlobStorageService] Obtendo connection string para company_id={company_id}, group_id={group_id}")
            conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
            if not conn_str:
                logger.error(f"[BlobStorageService] Connection string não encontrada para company_id={company_id}, group_id={group_id}")
                raise Exception("Connection string do Blob Storage não encontrada.")

            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(company_id)
                if not await container_client.exists():
                    logger.info(f"[BlobStorageService] Container '{company_id}' não existe. Criando...")
                    await container_client.create_container()
                blob_client = container_client.get_blob_client(blob_path)
                await blob_client.upload_blob(file_content, overwrite=True)
                logger.info(f"[BlobStorageService] Documento salvo em: {full_blob_path}")
                return full_blob_path
        except Exception as e:
            logger.error(f"[BlobStorageService] Falha ao salvar documento: {e}")
            raise

blob_storage_service = BlobStorageService()
