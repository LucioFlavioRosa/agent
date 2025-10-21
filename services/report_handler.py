from tools.blob_url_builder import BlobUrlBuilder

class ReportHandler:
    def __init__(self, blob_storage, blob_url_builder=None):
        self.blob_storage = blob_storage
        self.blob_url_builder = blob_url_builder or BlobUrlBuilder()
    @staticmethod
    def extract_report_text(step_result):
        if not step_result:
            return None
        if isinstance(step_result, dict):
            if 'relatorio' in step_result:
                return step_result['relatorio']
            if 'resultado' in step_result and isinstance(step_result['resultado'], dict):
                if 'relatorio' in step_result['resultado']:
                    return step_result['resultado']['relatorio']
        return None
    def try_read_existing_report(self, job_id, job_info, current_step_index):
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name')
        analysis_name = job_info['data'].get('analysis_name')
        report_blob_url = None
        try:
            report_text = self.blob_storage.read_report(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
            blob_path = self.blob_url_builder.build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
            report_blob_url = self.blob_url_builder.build_full_url(blob_path)
            if report_blob_url:
                try:
                    self.blob_storage.update_job_tracker(report_blob_url, job_id)
                except Exception as e:
                    print(f"[ReportHandler] Warning: Failed to update job tracker after reading report: {e}")
            return report_text
        except Exception as e:
            print(f"[ReportHandler] Warning: Failed to read report or update tracker: {e}")
            return None
    def save_report_to_blob(self, job_id, job_info, report_text, report_generated_by_agent=False):
        print(f"[ReportHandler.save_report_to_blob] INÍCIO do salvamento do relatório para job_id={job_id}")
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name')
        analysis_name = job_info['data'].get('analysis_name')
        print(f"[ReportHandler.save_report_to_blob] Parâmetros recebidos: projeto={projeto}, analysis_type={analysis_type}, repository_type={repository_type}, repo_name={repo_name}, branch_name={branch_name}, analysis_name={analysis_name}")
        print(f"[{job_id}] [save_report_to_blob] Iniciando salvamento. Tamanho do relatório: {len(report_text) if report_text else 0}, report_generated_by_agent: {report_generated_by_agent}")
        if report_generated_by_agent:
            print(f"[{job_id}] Salvando relatório gerado pelo agente no Blob Storage (gerar_novo_relatorio era False, mas relatório não foi encontrado).")
        url = None
        try:
            url = self.blob_storage.upload_report(report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
            print(f"[{job_id}] [save_report_to_blob] Upload concluído. URL retornada: {url}")
        except Exception as upload_error:
            print(f"[{job_id}] [ReportHandler.save_report_to_blob] ERRO durante upload do relatório para o Blob Storage: {upload_error}")
            raise
        if not url:
            print(f"[{job_id}] [ReportHandler.save_report_to_blob] ERRO: Blob Storage não retornou URL válida")
            raise ValueError(f"[{job_id}] ERRO: Blob Storage não retornou URL válida")
        job_info['data']['report_blob_url'] = url
        job_info['data']['analysis_report'] = report_text
        print(f"[{job_id}] Relatório salvo no Blob Storage: {url} (tamanho: {len(report_text) if report_text else 0} chars)")
        try:
            self.blob_storage.update_job_tracker(url, job_id)
            print(f"[{job_id}] [save_report_to_blob] Job tracker atualizado com sucesso para o relatório: {url}")
        except Exception as tracker_error:
            print(f"[{job_id}] [ReportHandler.save_report_to_blob] Warning: Falha ao atualizar job tracker após salvar relatório: {tracker_error}")
        return url
    def handle_report_only_mode(self, job_id, job_info, step_result):
        report_text = self.extract_report_text(step_result)
        if not report_text or len(report_text.strip()) == 0:
            raise ValueError(f"[{job_id}] ERRO: Tentativa de salvar relatório vazio no modo report_only")
        job_info['data']['analysis_report'] = report_text
        url = self.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] Modo report_only: Relatório salvo com sucesso ({len(report_text)} chars)")
        return url
    def validate_and_parse_blob_report(self, report_text, job_id):
        if not report_text or not isinstance(report_text, str):
            print(f"[{job_id}] ERRO: Relatório lido do Blob é inválido. Tipo: {type(report_text)}")
            return None
        if len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório lido do Blob está vazio.")
            return None
        print(f"[{job_id}] Relatório válido lido do Blob Storage ({len(report_text)} chars).")
        return report_text
