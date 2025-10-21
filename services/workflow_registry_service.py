from services.workflow_registry_loader import WorkflowRegistryLoader

class WorkflowRegistryService:
    def __init__(self):
        self._workflow_registry = None
        self._valid_analysis_types = None

    def get_workflow_registry(self):
        if self._workflow_registry is None:
            self._workflow_registry = WorkflowRegistryLoader.load_registry()
        return self._workflow_registry

    def get_valid_analysis_types(self):
        if self._valid_analysis_types is None:
            registry = self.get_workflow_registry()
            self._valid_analysis_types = list(registry.keys())
        return self._valid_analysis_types
