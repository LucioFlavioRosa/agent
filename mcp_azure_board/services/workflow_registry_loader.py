import yaml

class WorkflowRegistryLoader:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self._registry = None
        self._valid_analysis_types = None

    def load_registry(self):
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)
        self._registry = workflows
        self._valid_analysis_types = list(workflows.keys())
        return self._registry

    def get_valid_analysis_types(self):
        if self._valid_analysis_types is None:
            self.load_registry()
        return self._valid_analysis_types
