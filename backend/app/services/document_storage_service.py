from backend.app.utils.blob_storage_helper import (
    upload_file_to_blob,
    generate_blob_path,
    save_markdown_report
)
from backend.app.models.analysis_types import get_report_filename
from azure.storage.blob.aio import BlobServiceClient

class DocumentStorageService:
    """
    Serviço para encapsular lógica de armazenamento de documentos e relatórios no Blob Storage.
    """
    @staticmethod
    async def save_input_document(company_id: str, email: str, project_id: str, job_id: str, file_content: bytes, original_filename: str, blob_conn_str: str, container_name: str) -> str:
        blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
        blob_path = generate_blob_path(company_id, email, project_id, job_id, original_filename)
        await upload_file_to_blob(blob_service_client, container_name, blob_path, file_content)
        return blob_path

    @staticmethod
    async def save_extra_comment(company_id: str, email: str, project_id: str, job_id: str, comment_text: str, blob_conn_str: str, container_name: str) -> str:
        blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
        base_path = generate_blob_path(company_id, email, project_id, job_id, "")
        filename = "comentario_extra.md"
        blob_path = f"{base_path}{filename}" if base_path.endswith("/") else f"{base_path}/{filename}"
        await upload_file_to_blob(blob_service_client, container_name, blob_path, comment_text.encode("utf-8"))
        return blob_path

    @staticmethod
    async def save_analysis_report(company_id: str, email: str, project_id: str, job_id: str, analysis_type: str, report_content: str, blob_conn_str: str, container_name: str) -> str:
        blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
        report_type = get_report_filename(analysis_type)
        base_path = generate_blob_path(company_id, email, project_id, job_id, "")
        blob_path = await save_markdown_report(blob_service_client, container_name, base_path, report_content, report_type)
        return blob_path
