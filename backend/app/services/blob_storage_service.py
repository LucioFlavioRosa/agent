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
        logger.info(f"blob_upload_iniciado | company_id={company_id} | project_id={project_id} | job_id={job_id} | filename={filename}")
        try:
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id, group_id, vault_type='infra')
            if not conn_str:
                logger.error(f"blob_upload_erro | company_id={company_id} | motivo=connection_string_nao_encontrada")
                raise Exception("Connection string do Blob Storage não encontrada.")
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(company_id)
                blob_client = container_client.get_blob_client(blob_path)
                try:
                    await blob_client.upload_blob(file_data, overwrite=True)
                except ResourceNotFoundError:
                    await container_client.create_container()
                    await blob_client.upload_blob(file_data, overwrite=True)
                # Obtém o tamanho do arquivo se possível
                file_size = None
                if isinstance(file_data, bytes):
                    file_size = len(file_data)
                elif hasattr(file_data, '__aiter__'):
                    # Não é possível determinar o tamanho de um stream sem ler
                    file_size = 'stream'
                logger.info(f"blob_upload_sucesso | company_id={company_id} | project_id={project_id} | job_id={job_id} | filename={filename} | blob_path={full_blob_path} | file_size={file_size}")
                return full_blob_path
        except Exception as e:
            logger.error(f"blob_upload_erro | company_id={company_id} | project_id={project_id} | job_id={job_id} | filename={filename} | erro={e}")
            raise

    async def download_document(
        self, 
        company_id: str, 
        blob_path: str, 
        group_id: Optional[str] = None
    ) -> bytes:
        logger.info(f"blob_download_iniciado | company_id={company_id} | blob_path={blob_path}")
        try:
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
            if not conn_str:
                logger.error(f"blob_download_erro | company_id={company_id} | blob_path={blob_path} | motivo=connection_string_nao_encontrada")
                raise Exception("Connection string do Blob Storage não encontrada.")

            caminho_real_blob = blob_path
            if blob_path.startswith(f"{company_id}/"):
                caminho_real_blob = blob_path.replace(f"{company_id}/", "", 1)
                
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                blob_client = blob_service_client.get_blob_client(container=company_id, blob=caminho_real_blob)
                stream = await blob_client.download_blob()
                file_bytes = await stream.readall()
                file_size = len(file_bytes)
                logger.info(f"blob_download_sucesso | company_id={company_id} | blob_path={blob_path} | file_size={file_size}")
                return file_bytes
        except ResourceNotFoundError:
            logger.error(f"blob_download_erro | company_id={company_id} | blob_path={blob_path} | motivo=arquivo_nao_encontrado")
            raise
        except Exception as e:
            logger.error(f"blob_download_erro | company_id={company_id} | blob_path={blob_path} | erro={e}")
            raise
