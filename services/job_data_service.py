from models import JobFields

class JobDataService:
    def __init__(self):
        pass

    def create_initial_job_data(self, payload_dict, normalized_repo_name, analysis_name):
        job_data = {}
        job_data[JobFields.REPO_NAME] = normalized_repo_name
        job_data[JobFields.ANALYSIS_NAME] = analysis_name
        job_data[JobFields.ORIGINAL_ANALYSIS_TYPE] = payload_dict.get('analysis_type')
        job_data[JobFields.PROJETO] = payload_dict.get('projeto')
        job_data[JobFields.REPOSITORY_TYPE] = payload_dict.get('repository_type')
        job_data[JobFields.REPO_NAME_MODERNIZADO] = payload_dict.get('repo_name_modernizado')
        job_data[JobFields.BRANCH_NAME_MODERNIZADO] = payload_dict.get('branch_name_modernizado')
        job_data[JobFields.REPO_NAME_ORIGINAL] = payload_dict.get('repo_name_original')
        job_data[JobFields.BRANCH_NAME_ORIGINAL] = payload_dict.get('branch_name_original')
        job_data[JobFields.INSTRUCOES_EXTRAS] = payload_dict.get('instrucoes_extras')
        job_data[JobFields.USAR_RAG] = bool(payload_dict.get('usar_rag', False))
        job_data[JobFields.GERAR_RELATORIO_APENAS] = bool(payload_dict.get('gerar_relatorio_apenas', False))
        job_data[JobFields.GERAR_NOVO_RELATORIO] = bool(payload_dict.get('gerar_novo_relatorio', True))
        job_data[JobFields.MODEL_NAME] = payload_dict.get('model_name')
        job_data[JobFields.ARQUIVOS_ESPECIFICOS] = payload_dict.get('arquivos_especificos')
        job_data[JobFields.RETORNAR_LISTA_ARQUIVOS] = bool(payload_dict.get('retornar_lista_arquivos', False))
        job_data[JobFields.MODO_ADICAO_INCREMENTAL] = bool(payload_dict.get('modo_adicao_incremental', False))
        job_data[JobFields.USUARIO_EXECUTOR] = payload_dict.get('usuario_executor')
        job_data[JobFields.EXECUTAR_STEPS_INCREMENTALMENTE] = bool(payload_dict.get('executar_steps_incrementalmente', False))
        job_data[JobFields.MAX_STEPS_PER_BATCH] = payload_dict.get('max_steps_per_batch', 3)
        executar_build_dotnet = payload_dict.get('executar_build_dotnet', False)
        if not isinstance(executar_build_dotnet, bool):
            executar_build_dotnet = bool(executar_build_dotnet)
        job_data[JobFields.EXECUTAR_BUILD_DOTNET] = executar_build_dotnet
        return job_data

    def create_derived_job_data(self, original_job, analysis_name, normalized_repo_name, report):
        job_data = dict(original_job[JobFields.DATA])
        job_data[JobFields.REPO_NAME] = normalized_repo_name
        job_data[JobFields.ANALYSIS_NAME] = analysis_name
        job_data[JobFields.ANALYSIS_REPORT] = report
        return job_data

    def generate_analysis_name(self, analysis_name, job_id):
        if analysis_name:
            return analysis_name
        return f"analysis-{job_id}"
