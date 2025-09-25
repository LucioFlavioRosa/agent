from typing import Dict, Any, Optional
import json

class ReportHandler:
    def __init__(self, blob_storage):
        self.blob_storage = blob_storage
    
    def try_read_existing_report(self, job_id: str, job_info: Dict[str, Any], current_step_index: int) -> Optional[Dict[str, Any]]:
        if not job_info['data'].get('gerar_novo_relatorio', True):
            analysis_name = job_info['data'].get('analysis_name')
            if analysis_name:
                try:
                    existing_report = self.blob_storage.read_report(analysis_name)
                    if existing_report:
                        print(f"[{job_id}] Relatório existente encontrado para analysis_name: {analysis_name}")
                        return existing_report
                except Exception as e:
                    print(f"[{job_id}] Erro ao ler relatório existente: {str(e)}")
        return None
    
    def extract_report_text(self, step_result: Dict[str, Any]) -> str:
        if isinstance(step_result, dict):
            return step_result.get('relatorio', '')
        return str(step_result)
    
    def save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str, report_generated_by_agent: bool = False) -> None:
        analysis_name = job_info['data'].get('analysis_name')
        if analysis_name and report_text:
            try:
                blob_url = self.blob_storage.save_report(analysis_name, report_text)
                job_info['data']['report_blob_url'] = blob_url
                print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
            except Exception as e:
                print(f"[{job_id}] Erro ao salvar relatório no Blob Storage: {str(e)}")
    
    def handle_report_only_mode(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Processando modo 'gerar_relatorio_apenas'")
        
        report_text = self.extract_report_text(step_result)
        
        if report_text:
            job_info['data']['analysis_report'] = report_text
            
            analysis_name = job_info['data'].get('analysis_name')
            if analysis_name:
                try:
                    blob_url = self.blob_storage.save_report(analysis_name, report_text)
                    job_info['data']['report_blob_url'] = blob_url
                    print(f"[{job_id}] Relatório salvo no Blob Storage em modo 'gerar_relatorio_apenas': {blob_url}")
                except Exception as e:
                    print(f"[{job_id}] Erro ao salvar relatório no Blob Storage em modo 'gerar_relatorio_apenas': {str(e)}")
            else:
                print(f"[{job_id}] AVISO: analysis_name não encontrado para salvar relatório no Blob Storage")
        else:
            print(f"[{job_id}] AVISO: Relatório vazio em modo 'gerar_relatorio_apenas'")