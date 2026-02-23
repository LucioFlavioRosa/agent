from typing import Optional, Dict
from backend.app.services.blob_storage_service import BlobStorageService

analysis_type_mapper = {
    "agent_epics_generator_digital": "epics",
    "agent_epics_reviwer_digital": "epics",
    "agent_features_generator_digital": "features",
    "agent_featuares_reviwer_digital": "features",
    "agent_timeline_generator_digital": "timeline",
    "agent_timeline_reviwer_digital": "timeline",
    "agent_risks_generator_digital": "risks",
    "agent_risks_reviwer_digital": "risks"
}

class AnalysisReport:
    def __init__(self, report_url: str, comentario_url: Optional[str], documento_url: Optional[str]):
        self.report_url = report_url
        self.comentario_url = comentario_url
        self.documento_url = documento_url

    def to_dict(self):
        return {
            "report_url": self.report_url,
            "comentario_url": self.comentario_url,
            "documento_url": self.documento_url
        }

class ReportStorageService:
    @staticmethod
    def blob_path_builder(task_data: dict, report_type: str, file_type: str) -> str:
        # file_type: 'relatorio', 'comentario_extra', 'documento_recebido'
        company_id = task_data.get("company_id")
        email = task_data.get("email") or "noemail"
        project_id = task_data.get("project_id")
        job_id = task_data.get("job_id")
        if file_type == "relatorio":
            return f"{company_id}/{email}/{project_id}/{job_id}/{report_type}.md"
        elif file_type == "comentario_extra":
            return f"{company_id}/{email}/{project_id}/{job_id}/comentario_extra.md"
        elif file_type == "documento_recebido":
            # Detecta extensão do arquivo
            doc_blob_path = task_data.get("documento_blob_path")
            if doc_blob_path:
                ext = doc_blob_path.split('.')[-1]
                return f"{company_id}/{email}/{project_id}/{job_id}/documento_recebido.{ext}"
            else:
                return f"{company_id}/{email}/{project_id}/{job_id}/documento_recebido"
        else:
            return f"{company_id}/{email}/{project_id}/{job_id}/{file_type}"

    @staticmethod
    async def save_analysis_report(task_data: dict, report_content: str, blob_conn_str: str, container: str) -> AnalysisReport:
        analysis_type = task_data.get("analysis_type")
        report_type = analysis_type_mapper.get(analysis_type, "report")
        # 1. Caminho do relatório
        relatorio_path = ReportStorageService.blob_path_builder(task_data, report_type, "relatorio")
        report_url = await BlobStorageService.upload_markdown(blob_conn_str, container, relatorio_path, report_content)
        # 2. Caminho do comentário_extra
        comentario_url = None
        comentario_extra = task_data.get("comentario_extra")
        if comentario_extra:
            comentario_path = ReportStorageService.blob_path_builder(task_data, report_type, "comentario_extra")
            comentario_url = await BlobStorageService.upload_markdown(blob_conn_str, container, comentario_path, comentario_extra)
        # 3. Caminho do documento recebido
        documento_url = None
        documento_blob_path = task_data.get("documento_blob_path")
        if documento_blob_path:
            # Busca o blob temporário e faz upload para o caminho final
            # Aqui assumimos que o documento já está no blob, então apenas copiamos
            async with BlobStorageService:
                # Simula download e re-upload
                async with BlobServiceClient.from_connection_string(blob_conn_str) as blob_service_client:
                    container_client = blob_service_client.get_container_client(container)
                    blob_client_temp = container_client.get_blob_client(documento_blob_path)
                    if await blob_client_temp.exists():
                        doc_bytes = await blob_client_temp.download_blob().readall()
                        documento_path = ReportStorageService.blob_path_builder(task_data, report_type, "documento_recebido")
                        documento_url = await BlobStorageService.upload_file(blob_conn_str, container, documento_path, doc_bytes)
        return AnalysisReport(report_url, comentario_url, documento_url)
