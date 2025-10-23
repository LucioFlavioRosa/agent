def create_initial_job_data(payload_dict, normalized_repo_name, analysis_name):
    job_info = {
        'status': 'starting',
        'data': {},
    }
    job_info['data']['repo_name'] = normalized_repo_name
    job_info['data']['analysis_name'] = analysis_name
    job_info['data']['analysis_type'] = payload_dict.get('analysis_type')
    job_info['data']['projeto'] = payload_dict.get('projeto')
    job_info['data']['model_name'] = payload_dict.get('model_name')
    job_info['data']['usar_rag'] = payload_dict.get('usar_rag', False)
    job_info['data']['gerar_relatorio_apenas'] = payload_dict.get('gerar_relatorio_apenas', False)
    job_info['data']['retornar_lista_arquivos'] = payload_dict.get('retornar_lista_arquivos', False)
    job_info['data']['executar_steps_incrementalmente'] = payload_dict.get('executar_steps_incrementalmente', True)
    job_info['data']['max_steps_per_batch'] = payload_dict.get('max_steps_per_batch', 3)
    job_info['data']['executar_build_dotnet'] = payload_dict.get('executar_build_dotnet', False)
    job_info['data']['criar_epicos_azure'] = payload_dict.get('criar_epicos_azure', False)
    job_info['data']['repository_type'] = payload_dict.get('repository_type')
    job_info['data']['repo_name_original'] = payload_dict.get('repo_name_original')
    job_info['data']['branch_name_original'] = payload_dict.get('branch_name_original')
    job_info['data']['branch_name_modernizado'] = payload_dict.get('branch_name_modernizado')
    job_info['data']['usuario_executor'] = payload_dict.get('usuario_executor')
    job_info['data']['instrucoes_extras'] = payload_dict.get('instrucoes_extras')
    job_info['data']['arquivos_especificos'] = payload_dict.get('arquivos_especificos')
    job_info['data']['epic_id'] = payload_dict.get('epic_id')
    if payload_dict.get('analysis_type') == 'criacao_tarefas_azure_devops':
        repo_name_modernizado = payload_dict.get('repo_name_modernizado', '')
        parts = repo_name_modernizado.split('/')
        if len(parts) == 2:
            job_info['data']['organization'] = parts[0]
            job_info['data']['project'] = parts[1]
        else:
            job_info['data']['organization'] = None
            job_info['data']['project'] = None
    return job_info
