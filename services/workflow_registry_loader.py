import yaml
from typing import Dict, Any

class WorkflowRegistryLoader:
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        self.workflow_file_path = workflow_file_path
    
    def load_workflows(self) -> Dict[str, Any]:
        print(f"Carregando workflows do arquivo: {self.workflow_file_path}")
        workflows = {}
        
        try:
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                for document in yaml.safe_load_all(f):
                    if document:
                        workflows.update(document)
        except yaml.YAMLError as e:
            print(f"Erro ao processar YAML em streaming: {e}")
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                workflows = yaml.safe_load(f)
        
        return workflows