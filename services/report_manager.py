import json
from typing import Dict, Any, Optional
from domain.interfaces.report_manager_interface import IReportManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from domain.interfaces.job_manager_interface import IJobManager

class ReportManager(IReportManager):
    def __init__(self, blob_storage: IBlobStorageService, job_manager: IJobManager):
        self.blob_storage = blob_storage
        self.job_manager = job_manager
    
    def try_read_existing_report(self, job_id: str, job_info: Dict[str, Any], current_step_index: int) -> Optional[Dict[str, Any]]:
        if current_step_index == 0:
            gerar_novo_relatorio = job_info['data'].get('gerar_novo_relatorio', True)
            analysis_name = job_info['data'].get('analysis_name')

            if not gerar_novo_relatorio and analysis_name:
                print(f"[{job_id}] gerar_novo_relatorio=False detectado. Tentando ler relatório existente do Blob Storage: {analysis_name}")
                try:
                    existing_report = self.blob_storage.read_report(
                        job_info['data']['projeto'],
                        job_info['data']['original_analysis_type'],
                        job_info['data']['repository_type'],
                        job_info['data']['repo_name'],
                        job_info['data'].get('branch_name', 'main'),
                        analysis_name
                    )

                    if existing_report:
                        print(f"[{job_id}] Relatório encontrado no Blob Storage, reutilizando relatório existente")
                        try:
                            blob_url = self.blob_storage.get_report_url(
                                job_info['data']['projeto'],
                                job_info['data']['original_analysis_type'],
                                job_info['data']['repository_type'],
                                job_info['data']['repo_name'],
                                job_info['data'].get('branch_name', 'main'),
                                analysis_name
                            )
                            job_info['data']['report_blob_url'] = blob_url
                        except Exception as url_e:
                            print(f"[{job_id}] Aviso: Não foi possível obter URL do blob: {url_e}")

                        return {
                            'resultado': {
                                'reposta_final': {
                                    'reposta_final': json.dumps({"relatorio": existing_report}, ensure_ascii=False)
                                }
                            }
                        }
                    else:
                        print(f"[{job_id}] Relatório não encontrado no Blob Storage, será gerado novo relatório via agente")
                        return None

                except Exception as e:
                    print(f"[{job_id}] Erro ao tentar ler relatório do Blob Storage: {e}. Gerando novo relatório via agente")
                    return None
            elif gerar_novo_relatorio:
                print(f"[{job_id}] gerar_novo_relatorio=True detectado. Gerando novo relatório via agente")
            else:
                print(f"[{job_id}] analysis_name não fornecido. Gerando novo relatório via agente")

        return None
    
    def save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str, report_generated_by_agent: bool) -> None:
        if not job_info['data'].get('gerar_novo_relatorio', True):
            print(f"[{job_id}] gerar_novo_relatorio=False - Abortando salvamento no Blob Storage")
            return

        if job_info['data'].get('analysis_name') and report_text and report_generated_by_agent:
            try:
                blob_url = self.blob_storage.upload_report(
                    report_text,
                    job_info['data']['projeto'],
                    job_info['data']['original_analysis_type'],
                    job_info['data']['repository_type'],
                    job_info['data']['repo_name'],
                    job_info['data'].get('branch_name', 'main'),
                    job_info['data']['analysis_name']
                )
                job_info['data']['report_blob_url'] = blob_url
                print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
            except Exception as e:
                print(f"[{job_id}] Erro ao salvar relatório no Blob Storage: {e}")
    
    def handle_report_only_mode(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any]) -> None:
        report_text = step_result.get("relatorio", json.dumps(step_result, indent=2, ensure_ascii=False))
        job_info['data']['analysis_report'] = report_text

        if job_info['data'].get('gerar_novo_relatorio', True):
            self.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
        else:
            print(f"[{job_id}] gerar_novo_relatorio=False - Não salvando relatório no Blob Storage")

        print(f"[{job_id}] Modo 'gerar_relatorio_apenas' ativo. Finalizando.")
        self.job_manager.update_job_status(job_id, 'completed')