import uuid
from typing import Optional
from models import JobStatus, JobFields

class JobDataService:
    def __init__(self):
        pass
        
    def _parse_repository_name(self, repo_name: str):
        parts = repo_name.split('/')
        if len(parts) < 2:
            return None, None
        organization = parts[0]
        project = parts[1]
        return organization, project

    def generate_analysis_name(self, provided_name: Optional[str], job_id: str) -> str:
        if provided_name:
            return provided_name
        analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
        print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
        return analysis_name
    
    def create_initial_job_data(self, payload_dict, repo_name, analysis_name):
        data = {}
        data[JobFields.REPO_NAME] = repo_name
        analysis_type = payload_dict.get('analysis_type')
        data[JobFields.PROJETO] = payload_dict.get('projeto')
        data[JobFields.ANALYSIS_NAME] = analysis_name
        data[JobFields.ORIGINAL_ANALYSIS_TYPE] = payload_dict.get('analysis_type')
        data[JobFields.INSTRUCOES_EXTRAS] = payload_dict.get('instrucoes_extras')
        data[JobFields.MODEL_NAME] = payload_dict.get('model_name')
        data[JobFields.GERAR_RELATORIO_APENAS] = payload_dict.get('gerar_relatorio_apenas', False)
        data[JobFields.ARQUIVOS_ESPECIFICOS] = payload_dict.get('arquivos_especificos')
        data[JobFields.REPOSITORY_TYPE] = payload_dict.get('repository_type')
        data[JobFields.BRANCH_NAME] = payload_dict.get('branch_name')
        data[JobFields.RETORNAR_LISTA_ARQUIVOS] = payload_dict.get('retornar_lista_arquivos', False)
        data[JobFields.USUARIO_EXECUTOR] = payload_dict.get('usuario_executor')
        data[JobFields.MAX_STEPS_PER_BATCH] = payload_dict.get('max_steps_per_batch', 3)
        executar_build_dotnet = payload_dict.get('executar_build_dotnet', False)
        if not isinstance(executar_build_dotnet, bool):
            executar_build_dotnet = bool(executar_build_dotnet)
        data[JobFields.EXECUTAR_BUILD_DOTNET] = executar_build_dotnet
        
        return {
            JobFields.STATUS: None,
            JobFields.DATA: data
        }
    
    def create_derived_job_data(self, original_job: dict, analysis_name: str, repo_name: str, report: str) -> dict:
        original_data = original_job[JobFields.DATA]
        return {
            JobFields.STATUS: JobStatus.STARTING,
            JobFields.DATA: {
                JobFields.REPO_NAME: repo_name,
                JobFields.PROJETO: original_data[JobFields.PROJETO],
                JobFields.BRANCH_NAME: original_data[JobFields.BRANCH_NAME],
                JobFields.ORIGINAL_ANALYSIS_TYPE: 'implementacao',
                JobFields.INSTRUCOES_EXTRAS: f"Gerar código baseado no seguinte relatório:\n\n{report}",
                JobFields.MODEL_NAME: original_data.get(JobFields.MODEL_NAME),
                JobFields.GERAR_RELATORIO_APENAS: False,
                JobFields.ARQUIVOS_ESPECIFICOS: original_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
                JobFields.ANALYSIS_NAME: f"{analysis_name}-implementation",
                JobFields.REPOSITORY_TYPE: original_data[JobFields.REPOSITORY_TYPE],
                JobFields.RETORNAR_LISTA_ARQUIVOS: original_data.get(JobFields.RETORNAR_LISTA_ARQUIVOS, False),
                JobFields.USUARIO_EXECUTOR: original_data.get(JobFields.USUARIO_EXECUTOR)
            },
            JobFields.ERROR_DETAILS: None
        }
