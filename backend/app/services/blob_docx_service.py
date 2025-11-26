from typing import Optional
from backend.app.services.blob_storage_service import BlobStorageService

class BlobDocxService:
    def __init__(self, blob_storage_service: Optional[BlobStorageService] = None):
        self.blob_storage_service = blob_storage_service or BlobStorageService()

    def save_docx_to_blob(self, usuario_executor: str, projeto: str, analysis_name: str, file_content: bytes) -> str:
        """
        Salva o arquivo DOCX no Blob Storage no caminho especificado e retorna a URL do blob.
        Caminho: {usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx
        """
        blob_path = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx"
        url = self.blob_storage_service.upload_file(blob_path, file_content, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        return url
