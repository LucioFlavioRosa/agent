from typing import Dict, Any, Optional
import uuid

class JobDataService:
    def create_initial_job_data(self, payload: Dict[str, Any], normalized_repo_name: Optional[str], analysis_name: Optional[str]) -> Dict[str, Any]:
        job_data = {
            'status': 'starting',
            'data': {
                'repo_name_modernizado': payload.get('repo_name_modernizado'),
                'branch_name_modernizado': payload.get('branch_name_modernizado'),
                'projeto': payload.get('projeto'),
                'analysis_type': payload.get('analysis_type'),
                'instrucoes_extras': payload.get('instrucoes_extras'),
                'usar_rag': payload.get('usar_rag', False),
                'gerar_relatorio_apenas': payload.get('gerar_relatorio_apenas', False),
                'model_name': payload.get('model_name'),
                'arquivos_especificos': payload.get('arquivos_especificos'),
                'analysis_name': analysis_name,
                'repository_type': payload.get('repository_type'),
                'repo_name_original': payload.get('repo_name_original'),
                'branch_name_original': payload.get('branch_name_original'),
                'retornar_lista_arquivos': payload.get('retornar_lista_arquivos', False),
                'usuario_executor': payload.get('usuario_executor'),
                'executar_steps_incrementalmente': payload.get('executar_steps_incrementalmente', True),
                'max_steps_per_batch': payload.get('max_steps_per_batch', 3)
            }
        }
        if normalized_repo_name:
            job_data['data']['repo_name'] = normalized_repo_name
        return job_data

    def create_derived_job_data(self, original_job: Dict[str, Any], analysis_name: str, normalized_repo_name: Optional[str], report: Optional[str]) -> Dict[str, Any]:
        original_data = original_job.get('data', {})
        derived_data = {
            'status': 'starting',
            'data': {
                'repo_name_modernizado': original_data.get('repo_name_modernizado'),
                'branch_name_modernizado': original_data.get('branch_name_modernizado'),
                'projeto': original_data.get('projeto'),
                'analysis_type': original_data.get('analysis_type'),
                'instrucoes_extras': original_data.get('instrucoes_extras'),
                'usar_rag': original_data.get('usar_rag', False),
                'gerar_relatorio_apenas': original_data.get('gerar_relatorio_apenas', False),
                'model_name': original_data.get('model_name'),
                'arquivos_especificos': original_data.get('arquivos_especificos'),
                'analysis_name': analysis_name,
                'repository_type': original_data.get('repository_type'),
                'repo_name_original': original_data.get('repo_name_original'),
                'branch_name_original': original_data.get('branch_name_original'),
                'retornar_lista_arquivos': original_data.get('retornar_lista_arquivos', False),
                'usuario_executor': original_data.get('usuario_executor'),
                'executar_steps_incrementalmente': original_data.get('executar_steps_incrementalmente', True),
                'max_steps_per_batch': original_data.get('max_steps_per_batch', 3),
                'analysis_report': report
            }
        }
        if normalized_repo_name:
            derived_data['data']['repo_name'] = normalized_repo_name
        return derived_data

    def generate_analysis_name(self, analysis_name: Optional[str], job_id: str) -> str:
        if analysis_name:
            return analysis_name
        return f"analysis-{job_id}"
