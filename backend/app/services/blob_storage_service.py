import logging
from typing import Optional, AsyncIterable, Union
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from backend.app.services.vault_service import VaultService

logger = logging.getLogger("mcp_blob_storage")

class BlobStorageService:
    def __init__(self, vault_service: VaultService):
        self.vault_service = vault_service
        
    async def save_document(
        self,
        company_id: str,
        project_id: str,
        job_id: str,
        file_data: Union[bytes, AsyncIterable[bytes]], # Suporta Bytes ou Stream
        filename: str,
        group_id: Optional[str] = None
    ) -> str:
        blob_path = f"{project_id}/{job_id}/{filename}"
        full_blob_path = f"{company_id}/{blob_path}"
        logger.info(f"[BlobStorageService] save_document chamado: company_id='{company_id}', project_id='{project_id}', job_id='{job_id}', filename='{filename}'")
        try:
            logger.info(f"[BlobStorageService] Obtendo connection string para company_id='{company_id}', group_id='{group_id}'")
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
            if not conn_str:
                logger.error(f"[BlobStorageService] Connection string não encontrada para company_id='{company_id}'")
                raise Exception("Connection string do Blob Storage não encontrada.")
            logger.info(f"[BlobStorageService] Connection string obtida com sucesso para company_id='{company_id}'")
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(company_id)
                blob_client = container_client.get_blob_client(blob_path)
                try:
                    logger.info(f"[BlobStorageService] Tentando upload direto para blob: '{full_blob_path}'")
                    await blob_client.upload_blob(file_data, overwrite=True)
                    logger.info(f"[BlobStorageService] Documento salvo direto em: '{full_blob_path}'")
                except ResourceNotFoundError:
                    logger.warning(f"[BlobStorageService] Container '{company_id}' não encontrado. Criando container...")
                    await container_client.create_container()
                    logger.info(f"[BlobStorageService] Container '{company_id}' criado com sucesso. Tentando upload novamente...")
                    await blob_client.upload_blob(file_data, overwrite=True)
                    logger.info(f"[BlobStorageService] Documento salvo em: '{full_blob_path}' (após criar container)")
                logger.info(f"[BlobStorageService] save_document finalizado com sucesso para blob: '{full_blob_path}'")
                return full_blob_path
        except Exception as e:
            logger.error(f"[BlobStorageService] Falha ao salvar documento em '{full_blob_path}': {e}", exc_info=True)
            raise

    async def download_document(
        self, 
        company_id: str, 
        blob_path: str, 
        group_id: Optional[str] = None
    ) -> bytes:
        logger.info(f"[BlobStorageService] download_document chamado: company_id='{company_id}', blob_path='{blob_path}', group_id='{group_id}'")
        try:
            logger.info(f"[BlobStorageService] Obtendo connection string para company_id='{company_id}', group_id='{group_id}'")
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
            if not conn_str:
                logger.error(f"[BlobStorageService] Connection string não encontrada para company_id='{company_id}'")
                raise Exception("Connection string do Blob Storage não encontrada.")
            logger.info(f"[BlobStorageService] Connection string obtida com sucesso para company_id='{company_id}'")
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                blob_client = blob_service_client.get_blob_client(container=company_id, blob=blob_path)
                logger.info(f"[BlobStorageService] Iniciando download do blob: '{blob_path}' do container: '{company_id}'")
                stream = await blob_client.download_blob()
                file_bytes = await stream.readall()
                logger.info(f"[BlobStorageService] Download concluído: {len(file_bytes)} bytes para blob: '{blob_path}'")
                return file_bytes
        except ResourceNotFoundError:
            logger.error(f"[BlobStorageService] Arquivo não encontrado no Blob Storage: '{blob_path}'", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[BlobStorageService] Erro ao baixar documento '{blob_path}': {e}", exc_info=True)
            raise
