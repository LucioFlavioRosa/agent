import logging
from azure.storage.blob.aio import BlobServiceClient
from backend.app.utils.blob_storage_helper import build_blob_path

logger = logging.getLogger("mcp_blob_service")

class BlobService:
    def __init__(self, vault_service):
        self.vault_service = vault_service

    async def upload_document(self, company_id: str, email: str, project_id: str, job_id: str, file_content: bytes, filename: str) -> str:
        """
        Faz upload de um documento para o Blob Storage.
        Retorna o caminho completo do blob (blob_path).
        """
        try:
            # 1. Busca a connection string no cofre
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id)
            if not conn_str:
                logger.error(f"❌ [BlobService] Connection string não encontrada para company_id={company_id}")
                raise Exception("Connection string do Blob Storage não encontrada.")
            # 2. Nome do container é o company_id
            container_name = company_id
            # 3. Constrói o caminho do blob
            blob_path = build_blob_path(company_id, email, project_id, job_id, filename)
            # 4. Upload
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(container_name)
                if not await container_client.exists():
                    await container_client.create_container()
                blob_client = container_client.get_blob_client(blob_path)
                await blob_client.upload_blob(file_content, overwrite=True)
            logger.info(f"✅ [BlobService] Documento '{filename}' salvo em '{blob_path}' no container '{container_name}'")
            return f"{container_name}/{blob_path}"
        except Exception as e:
            logger.error(f"❌ [BlobService] Falha ao fazer upload: {e}")
            raise