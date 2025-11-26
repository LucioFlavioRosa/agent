import os
import yaml
from services.workflow_registry_service import WorkflowRegistryService

class AzureWorkflowRegistryService(WorkflowRegistryService):
    AZURE_WORKFLOWS_PATH = os.path.join(os.path.dirname(__file__), '..', 'workflows_azure.yaml')
    _VALID_ANALYSIS_TYPES = [
        'criacao_epicos_azure_devops',
        'criacao_tarefas_azure_devops',
        'revisor_tarefas',
        'criacao_features_azure_devops'
    ]

    def __init__(self):
        super().__init__()
        self._workflow_registry = self._load_azure_workflows()

    def _load_azure_workflows(self):
        with open(self.AZURE_WORKFLOWS_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_workflow_registry(self):
        return self._workflow_registry

    def get_valid_analysis_types(self):
        return self._VALID_ANALYSIS_TYPES
