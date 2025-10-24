class JobDataService:
    def create_initial_job_data(self, payload_dict, normalized_repo_name, analysis_name):
        job_info = {
            'status': 'starting',
            'data': {
                'repo_name': normalized_repo_name,
                'analysis_name': analysis_name,
                'criar_tarefas_azure': payload_dict.get('criar_tarefas_azure', False),
                # ... outros campos copiados do payload_dict ...
            }
        }
        for key, value in payload_dict.items():
            if key not in job_info['data']:
                job_info['data'][key] = value
        print(f"[JobDataService-DEBUG] criar_tarefas_azure propagado: {job_info['data'].get('criar_tarefas_azure')}")
        return job_info
