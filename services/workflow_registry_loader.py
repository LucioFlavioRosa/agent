from typing import Dict, Any
import yaml

class WorkflowRegistryLoader:
    def __init__(self, workflow_file_path: str):
        self.workflow_file_path = workflow_file_path

    def load_workflows(self) -> Dict[str, Any]:
        with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
            raw_yaml = yaml.safe_load(f)
        # Não há mais lógica de filtragem de agentes, retorna todos os workflows
        return raw_yaml.get('workflows', {})
