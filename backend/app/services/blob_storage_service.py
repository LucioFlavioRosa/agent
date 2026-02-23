import logging
from typing import Optional
from fastapi import UploadFile
from azure.storage.blob.aio import BlobServiceClient
from backend.app.services.vault_service import vault_service
from backend.app.config.settings import settings
from backend.app.exceptions.blob_exceptions import BlobValidationError

logger = logging.getLogger("mcp_blob_storage")

class BlobStorageService:
    """
    Serviço para upload de documentos no Azure Blob Storage.
    
    O caminho de armazenamento segue a estrutura:
      company_id/project_id/job_id/filename
    
    Métodos:
        upload_document(company_id, project_id, job_id, file):
            Faz upload do arquivo para o Blob Storage, realizando validações e garantindo existência do container.
    
    Exemplos:
        >>> blob_service = BlobStorageService()
        >>> await blob_service.upload_document("acme", "proj1", "job42", file)
    """

    async def upload_document(self, company_id: str, project_id: str, job_id: str, file: UploadFile) -> str:
        """
        Faz upload de um documento para o Blob Storage.
        
        Args:
            company_id (str): Nome da empresa, usado como nome do container.
            project_id (str): ID do projeto.
            job_id (str): ID do job.
            file (UploadFile): Arquivo recebido via FastAPI.
        
        Returns:
            str: Caminho completo do arquivo no Blob Storage (company_id/project_id/job_id/filename).
        
        Raises:
            BlobValidationError: Se validações de tamanho ou extensão falharem.
            Exception: Para falhas de conexão ou upload.
        
        Exemplo:
            caminho = await blob_service.upload_document("acme", "proj1", "job42", file)
        """
        logger.info(f"Iniciando upload de documento para company_id={company_id}, project_id={project_id}, job_id={job_id}, filename={file.filename}")
        # Validação de tamanho
        file_bytes = await file.read()
        max_size_mb = getattr(settings, 'BLOB_UPLOAD_MAX_SIZE_MB', 20)
        allowed_extensions = getattr(settings, 'BLOB_ALLOWED_EXTENSIONS', ['.docx', '.pdf'])
        file_size_mb = len(file_bytes) / (1024 * 1024)
        ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_size_mb > max_size_mb:
            logger.error(f"Arquivo excede limite de tamanho: {file_size_mb:.2f}MB > {max_size_mb}MB")
            raise BlobValidationError(f"Arquivo excede limite de tamanho de {max_size_mb}MB.")
        if ext not in allowed_extensions:
            logger.error(f"Extensão não permitida: {ext}. Permitidas: {allowed_extensions}")
            raise BlobValidationError(f"Extensão '{ext}' não permitida. Permitidas: {allowed_extensions}")
        # Busca connection string no cofre
        try:
            conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id)
            if not conn_str:
                logger.error(f"Connection string não encontrada para company_id={company_id}")
                raise Exception("Connection string não encontrada no Vault.")
        except Exception as e:
            logger.error(f"Erro ao buscar connection string: {e}")
            raise
        # Upload para Blob Storage
        blob_path = f"{project_id}/{job_id}/{file.filename}"
        try:
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(company_id)
                await self._ensure_container_exists(container_client)
                blob_client = container_client.get_blob_client(blob_path)
                await blob_client.upload_blob(file_bytes, overwrite=True)
                logger.info(f"Upload realizado com sucesso: {company_id}/{blob_path}")
                return f"{company_id}/{blob_path}"
        except Exception as e:
            logger.error(f"Falha no upload para Blob Storage: {e}")
            raise

    async def _ensure_container_exists(self, container_client) -> None:
        """
        Garante que o container existe, criando se necessário.
        
        Args:
            container_client: Instância do ContainerClient.
        
        Returns:
            None
        """
        exists = await container_client.exists()
        if not exists:
            logger.info(f"Container '{container_client.container_name}' não existe. Criando...")
            await container_client.create_container()
            logger.info(f"Container '{container_client.container_name}' criado com sucesso.")
