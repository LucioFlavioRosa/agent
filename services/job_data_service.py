from tools.conectores.azure_conector import AzureConector

class JobDataService:
    def create_initial_job_data(self, payload, normalized_repo_name, analysis_name):
        data = {
            'repo_name': normalized_repo_name,
            'analysis_name': analysis_name,
            # ... outros campos padrão ...
        }
        # Lógica para extrair organização e projeto se criar_epicos_azure=True
        if payload.get('criar_epicos_azure'):
            organization, project, _ = AzureConector._parse_repository_name(normalized_repo_name)
            data['azure_organization'] = organization
            data['azure_project'] = project
        # ... resto da lógica padrão ...
        return {
            'data': data,
            # ... outros campos do job ...
        }
