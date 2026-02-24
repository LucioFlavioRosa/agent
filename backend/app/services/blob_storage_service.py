import logging
from typing import Optional, AsyncIterable, Union
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from backend.app.services.vault_service import vault_service

logger = logging.getLogger("mcp_blob_storage")

class BlobStorageService:
    async def save_document(
        self,
        company_id: str,
        project_id: str,
        job_id: str,
        file_data: Union[bytes, AsyncIterable[bytes]], # Suporta Bytes ou Stream
        filename: str,
        group_id: Optional[str] = None
    ) -> str:
        """
        Salva um documento no Azure Blob Storage usando Streaming ou Bytes inteiros.
        - Tenta criar o container, ignorando erro se já existir (Otimização de request).
        """
        blob_path = f"{project_id}/{job_id}/{filename}"
        full_blob_path = f"{company_id}/{blob_path}"
        
        try:
            logger.info(f"[BlobStorageService] Obtendo connection string para company_id={company_id}, group_id={group_id}")
            conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
            if not conn_str:
                logger.error(f"[BlobStorageService] Connection string não encontrada para company_id={company_id}")
                raise Exception("Connection string do Blob Storage não encontrada.")

            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(company_id)
                
                # --- OTIMIZAÇÃO: Tenta criar e trata o erro ao invés de usar exists() ---
                try:
                    await container_client.create_container()
                    logger.info(f"[BlobStorageService] Container '{company_id}' criado com sucesso.")
                except ResourceExistsError:
                    # O container já existe, não precisamos fazer nada
                    pass
                
                blob_client = container_client.get_blob_client(blob_path)
                
                # O Azure Blob SDK entende nativamente um AsyncIterable e faz o upload em chunks
                await blob_client.upload_blob(file_data, overwrite=True)
                
                logger.info(f"[BlobStorageService] Documento salvo em: {full_blob_path}")
                return full_blob_path
                
        except Exception as e:
            logger.error(f"[BlobStorageService] Falha ao salvar documento: {e}")
            raise

blob_storage_service = BlobStorageService()
