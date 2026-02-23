import os
from typing import Any

async def upload_file_to_blob(blob_service_client: Any, container_name: str, blob_path: str, content: bytes) -> None:
    """
    Faz upload genérico de um arquivo para o Blob Storage.
    """
    container_client = blob_service_client.get_container_client(container_name)
    if not await container_client.exists():
        await container_client.create_container()
    blob_client = container_client.get_blob_client(blob_path)
    await blob_client.upload_blob(content, overwrite=True)


def generate_blob_path(company_id: str, email: str, project_id: str, job_id: str, filename: str) -> str:
    """
    Gera caminho padronizado para salvar arquivos no Blob Storage.
    Estrutura: company_id/email/project_id/job_id/filename
    """
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return f"{company_id}/{safe_email}/{project_id}/{job_id}/{filename}"


async def save_markdown_report(blob_service_client: Any, container_name: str, base_path: str, report_content: str, report_type: str) -> str:
    """
    Salva relatório markdown com nomenclatura baseada no tipo de análise.
    Retorna o caminho do blob salvo.
    """
    filename = f"{report_type}.md"
    blob_path = os.path.join(base_path, filename)
    await upload_file_to_blob(blob_service_client, container_name, blob_path, report_content.encode("utf-8"))
    return blob_path
