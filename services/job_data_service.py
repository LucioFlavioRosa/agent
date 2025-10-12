from models import JobFields

class JobDataService:
    def __init__(self):
        pass

    def create_initial_job_data(self, payload_dict, normalized_repo_name, analysis_name):
        data = {}
        data[JobFields.REPO_NAME] = normalized_repo_name
        data[JobFields.PROJETO] = payload_dict.get('projeto')
        data[JobFields.ANALYSIS_NAME] = analysis_name
        data[JobFields.ANALYSIS_TYPE] = payload_dict.get('analysis_type')
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
