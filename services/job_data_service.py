import uuid
from typing import Optional
from models import JobStatus, JobFields

class JobDataService:
    """Serviço responsável por criação e manipulação de dados de jobs."""
    
    def generate_analysis_name(self, provided_name: Optional[str], job_id: str) -> str:
        """Gera nome de análise automaticamente se não fornecido."""
        if provided_name:
            return provided_name
        
        analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
        print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
        return analysis_name
    
    def create_initial_job_data(self, payload_dict: dict, normalized_repo_name: str, analysis_name: str) -> dict:
        """Cria estrutura inicial de dados do job."""
        return {
            JobFields.STATUS: JobStatus.STARTING,
            JobFields.DATA: {
                JobFields.REPO_NAME: normalized_repo_name,
                JobFields.ORIGINAL_REPO_NAME: payload_dict.get('repo_name_modernizado'),
                JobFields.PROJETO: payload_dict.get('projeto'),
                JobFields.BRANCH_NAME: payload_dict.get('branch_name_modernizado'),
                JobFields.ORIGINAL_ANALYSIS_TYPE: payload_dict.get('analysis_type'),
                JobFields.INSTRUCOES_EXTRAS: payload_dict.get('instrucoes_extras'),
                JobFields.MODEL_NAME: payload_dict.get('model_name'),
                JobFields.USAR_RAG: payload_dict.get('usar_rag', False),
                JobFields.GERAR_RELATORIO_APENAS: payload_dict.get('gerar_relatorio_apenas', False),
                JobFields.GERAR_NOVO_RELATORIO: payload_dict.get('gerar_novo_relatorio', True),
                JobFields.ARQUIVOS_ESPECIFICOS: payload_dict.get('arquivos_especificos'),
                JobFields.ANALYSIS_NAME: analysis_name,
                JobFields.REPOSITORY_TYPE: payload_dict.get('repository_type'),
                JobFields.REPO_NAME_MODERNIZADO: payload_dict.get('repo_name_modernizado'),
                JobFields.BRANCH_NAME_MODERNIZADO: payload_dict.get('branch_name_modernizado'),
                JobFields.REPO_NAME_ORIGINAL: payload_dict.get('repo_name_original'),
                JobFields.BRANCH_NAME_ORIGINAL: payload_dict.get('branch_name_original'),
                JobFields.RETORNAR_LISTA_ARQUIVOS: payload_dict.get('retornar_lista_arquivos', False),
                JobFields.MODO_ADICAO_INCREMENTAL: payload_dict.get('modo_adicao_incremental', False),
                JobFields.USUARIO_EXECUTOR: payload_dict.get('usuario_executor')
            },
            JobFields.ERROR_DETAILS: None
        }
    
    def create_derived_job_data(self, original_job: dict, analysis_name: str, normalized_repo_name: str, report: str) -> dict:
        """Cria dados de job derivado para implementação baseada em relatório."""
        original_data = original_job[JobFields.DATA]
        return {
            JobFields.STATUS: JobStatus.STARTING,
            JobFields.DATA: {
                JobFields.REPO_NAME: normalized_repo_name,
                JobFields.ORIGINAL_REPO_NAME: original_data[JobFields.REPO_NAME],
                JobFields.PROJETO: original_data[JobFields.PROJETO],
                JobFields.BRANCH_NAME: original_data[JobFields.BRANCH_NAME],
                JobFields.ORIGINAL_ANALYSIS_TYPE: 'implementacao',
                JobFields.INSTRUCOES_EXTRAS: f"Gerar código baseado no seguinte relatório:\n\n{report}",
                JobFields.MODEL_NAME: original_data.get(JobFields.MODEL_NAME),
                JobFields.USAR_RAG: original_data.get(JobFields.USAR_RAG, False),
                JobFields.GERAR_RELATORIO_APENAS: False,
                JobFields.GERAR_NOVO_RELATORIO: True,
                JobFields.ARQUIVOS_ESPECIFICOS: original_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
                JobFields.ANALYSIS_NAME: f"{analysis_name}-implementation",
                JobFields.REPOSITORY_TYPE: original_data[JobFields.REPOSITORY_TYPE],
                JobFields.RETORNAR_LISTA_ARQUIVOS: original_data.get(JobFields.RETORNAR_LISTA_ARQUIVOS, False),
                JobFields.MODO_ADICAO_INCREMENTAL: original_data.get(JobFields.MODO_ADICAO_INCREMENTAL, False),
                JobFields.USUARIO_EXECUTOR: original_data.get(JobFields.USUARIO_EXECUTOR)
            },
            JobFields.ERROR_DETAILS: None
        }
