import os
from services.workflow_registry_loader import WorkflowRegistryLoader

class WorkflowRegistryService:
    def __init__(self):
        self._workflow_registry = None
        self._valid_analysis_types = None
        self._load_registry()

    def _load_registry(self):
        workflow_yaml_path = os.getenv('WORKFLOW_YAML_PATH', 'workflows.yaml')
        loader = WorkflowRegistryLoader(workflow_yaml_path)
        self._workflow_registry = loader.load_registry()
        self._valid_analysis_types = loader.get_valid_analysis_types()

    def get_workflow_registry(self):
        return self._workflow_registry

    def get_valid_analysis_types(self):
        return self._valid_analysis_types
