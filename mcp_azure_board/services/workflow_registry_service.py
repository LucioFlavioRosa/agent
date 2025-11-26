import yaml
import os
class WorkflowRegistryService:
    def __init__(self, workflow_registry_path: str = None):
        self.workflow_registry_path = workflow_registry_path or os.getenv("WORKFLOW_REGISTRY_PATH", "workflows.yaml")
        self._workflow_registry = None
        self._valid_analysis_types = None
        self._load_registry()
    def _load_registry(self):
        if not os.path.exists(self.workflow_registry_path):
            raise FileNotFoundError(f"Workflow registry file not found: {self.workflow_registry_path}")
        with open(self.workflow_registry_path, "r", encoding="utf-8") as f:
            self._workflow_registry = yaml.safe_load(f)
        self._valid_analysis_types = list(self._workflow_registry.keys())
    def get_workflow_registry(self):
        return self._workflow_registry
    def get_valid_analysis_types(self):
        return self._valid_analysis_types