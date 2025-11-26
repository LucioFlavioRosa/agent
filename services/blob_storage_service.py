class BlobStorageService:
    def __init__(self, config):
        self.config = config

    def save_report(self, job_id, job_info, report_text):
        # Implementação agnóstica, pode ser Azure, S3, etc.
        # Aqui apenas um stub, real implementação depende da plataforma
        # Exemplo: return azure_blob_client.upload_report(...)
        raise NotImplementedError("Implementação de save_report deve ser fornecida pela plataforma específica.")

    def get_report_url(self, **kwargs):
        # Retorna URL do relatório, independente de plataforma
        raise NotImplementedError("Implementação de get_report_url deve ser fornecida pela plataforma específica.")
