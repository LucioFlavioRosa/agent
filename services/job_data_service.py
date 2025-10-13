import uuid
from typing import Optional
from models import JobStatus, JobFields

class JobDataService:

    def __init__(self):
        pass
        
    def generate_analysis_name(self, provided_name: Optional[str], job_id: str) -> str:
        if provided_name:
            return provided_name
        analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
        print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
        return analysis_name
    
    def create_initial_job_data(self, payload_dict, normalized_repo_name, analysis_name):
        data = {}
        data[JobFields.REPO_NAME] = normalized_repo_name
        data[JobFields.PROJETO] = payload_dict.get('projeto')
        data[JobFields.ANALYSIS_NAME] = analysis_name
        data[JobFields.ORIGINAL_ANALYSIS_TYPE] = payload_dict.get('analysis_type')
        data[JobFields.INSTRUCOES_EXTRAS] = payload_dict.get('instrucoes_extras')
        data[JobFields.MODEL_NAME] = payload_dict.get('model_name')
        data[JobFields.USAR_RAG] = payload_dict.get('usar_rag', False)
        data[JobFields.GERAR_RELATORIO_APENAS] = payload_dict.get('gerar_relatorio_apenas', False)
        data[JobFields.GERAR_NOVO_RELATORIO] = payload_dict.get('gerar_novo_relatorio', True)
        data[JobFields.ARQUIVOS_ESPECIFICOS] = payload_dict.get('arquivos_especificos')
        data[JobFields.REPOSITORY_TYPE] = payload_dict.get('repository_type')
        data[JobFields.REPO_NAME_MODERNIZADO] = payload_dict.get('repo_name_modernizado')
        data[JobFields.BRANCH_NAME_MODERNIZADO] = payload_dict.get('branch_name_modernizado')
        data[JobFields.REPO_NAME_ORIGINAL] = payload_dict.get('repo_name_original')
        data[JobFields.BRANCH_NAME_ORIGINAL] = payload_dict.get('branch_name_original')
        data[JobFields.RETORNAR_LISTA_ARQUIVOS] = payload_dict.get('retornar_lista_arquivos', False)
        data[JobFields.MODO_ADICAO_INCREMENTAL] = payload_dict.get('modo_adicao_incremental', False)
        data[JobFields.USUARIO_EXECUTOR] = payload_dict.get('usuario_executor')
        data[JobFields.EXECUTAR_STEPS_INCREMENTALMENTE] = payload_dict.get('executar_steps_incrementalmente', False)
        data[JobFields.MAX_STEPS_PER_BATCH] = payload_dict.get('max_steps_per_batch', 3)
        executar_build_dotnet = payload_dict.get('executar_build_dotnet', False)
        if not isinstance(executar_build_dotnet, bool):
            executar_build_dotnet = bool(executar_build_dotnet)
        data[JobFields.EXECUTAR_BUILD_DOTNET] = executar_build_dotnet
        
        return {
            JobFields.STATUS: None,
            JobFields.DATA: data
        }
    def create_derived_job_data(self, original_job: dict, analysis_name: str, normalized_repo_name: str, report: str) -> dict:
        original_data = original_job[JobFields.DATA]
        return {
            JobFields.STATUS: JobStatus.STARTING,
            JobFields.DATA: {
                JobFields.REPO_NAME: normalized_repo_name,
                JobFields.PROJETO: payload.get('projeto'),
                JobFields.ANALYSIS_NAME: analysis_name,
                JobFields.ORIGINAL_ANALYSIS_TYPE: payload.get('analysis_type'),
                JobFields.REPOSITORY_TYPE: payload.get('repository_type'),
                JobFields.REPO_NAME_MODERNIZADO: payload.get('repo_name_modernizado'),
                JobFields.BRANCH_NAME_MODERNIZADO: payload.get('branch_name_modernizado'),
                JobFields.REPO_NAME_ORIGINAL: payload.get('repo_name_original'),
                JobFields.BRANCH_NAME_ORIGINAL: payload.get('branch_name_original'),
                JobFields.INSTRUCOES_EXTRAS: payload.get('instrucoes_extras'),
                JobFields.USAR_RAG: payload.get('usar_rag', False),
                JobFields.GERAR_RELATORIO_APENAS: payload.get('gerar_relatorio_apenas', False),
                JobFields.GERAR_NOVO_RELATORIO: payload.get('gerar_novo_relatorio', True),
                JobFields.MODEL_NAME: payload.get('model_name'),
                JobFields.ARQUIVOS_ESPECIFICOS: payload.get('arquivos_especificos'),
                JobFields.RETORNAR_LISTA_ARQUIVOS: payload.get('retornar_lista_arquivos', False),
                JobFields.MODO_ADICAO_INCREMENTAL: payload.get('modo_adicao_incremental', False),
                JobFields.USUARIO_EXECUTOR: payload.get('usuario_executor'),
                JobFields.EXECUTAR_STEPS_INCREMENTALMENTE: payload.get('executar_steps_incrementalmente', False),
                JobFields.MAX_STEPS_PER_BATCH: payload.get('max_steps_per_batch', 3),
                JobFields.EXECUTAR_BUILD_DOTNET: payload.get('executar_build_dotnet', False)
            }
        }
        if 'git_username' in payload and payload['git_username'] is not None:
            job_data[JobFields.DATA][JobFields.GIT_USERNAME] = payload['git_username']
        if 'git_token' in payload and payload['git_token'] is not None:
            job_data[JobFields.DATA][JobFields.GIT_TOKEN] = payload['git_token']
        return job_data
