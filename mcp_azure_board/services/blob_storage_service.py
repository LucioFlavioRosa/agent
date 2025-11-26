import os
from typing import Optional

class BlobStorageService:
    def __init__(self, blob_client):
        self.blob_client = blob_client

    def save_report_to_blob(self, job_id: str, job_info: dict, report_text: str) -> Optional[str]:
        """
        Salva o relatório no Blob Storage no caminho correto:
        {usuario_executor}/{projeto}/relatorios/{analysis_type}/{analysis_name}.md
        """
        usuario_executor = job_info['data'].get('usuario_executor')
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type') or job_info['data'].get('analysis_type')
        analysis_name = job_info['data'].get('analysis_name')
        if not all([usuario_executor, projeto, analysis_type, analysis_name]):
            raise ValueError("Campos obrigatórios ausentes para salvar o relatório no Blob Storage.")
        blob_folder = f"{usuario_executor}/{projeto}/relatorios/{analysis_type}"
        blob_filename = f"{analysis_name}.md"
        blob_path = os.path.join(blob_folder, blob_filename)
        # Salva o relatório no Blob Storage
        self.blob_client.upload_blob(blob_path, report_text.encode('utf-8'), overwrite=True)
        # Retorna a URL do blob salvo
        blob_url = self.blob_client.get_blob_url(blob_path)
        return blob_url
