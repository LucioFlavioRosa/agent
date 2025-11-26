class DependencyContainer:
    def __init__(self):
        self._services = {}
        self._init_services()

    def _init_services(self):
        # Removido: Criação de azure_board_service e dependências exclusivas do Azure Boards
        pass

    def get_workflow_registry_service(self):
        return self._services.get('workflow_registry_service')

    def get_job_store(self):
        return self._services.get('job_store')

    def get_analysis_name_service(self):
        return self._services.get('analysis_name_service')

    def get_redis_cache_service(self):
        return self._services.get('redis_cache_service')
