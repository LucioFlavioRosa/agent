import yaml
import os

class WorkflowRegistryLoader:
    def __init__(self, workflow_yaml_path=None):
        self.workflow_yaml_path = workflow_yaml_path or os.path.join(os.path.dirname(__file__), '..', 'workflows.yaml')
        self._registry = None

    def load_registry(self):
        if self._registry is not None:
            return self._registry
        with open(self.workflow_yaml_path, 'r', encoding='utf-8') as f:
            self._registry = yaml.safe_load(f)
        return self._registry

    def get_workflow(self, analysis_type):
        registry = self.load_registry()
        return registry.get(analysis_type)

    def get_all_workflows(self):
        return self.load_registry()
