from typing import Dict, Any
from models import JobFields
class JobDataService:
    def create_initial_job_data(self, payload: Dict[str, Any], normalized_repo_name: str, analysis_name: str) -> Dict[str, Any]:
        job_data = {
            JobFields.STATUS: 'starting',
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
