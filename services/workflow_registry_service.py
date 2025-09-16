import yaml
import enum
from typing import Dict, Any

class WorkflowRegistryService:
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        self.workflow_file_path = workflow_file_path
        self._workflow_registry = None
        self._valid_analysis_types = None
        self.registry = self._load()

    
    def load_workflow_registry(self) -> Dict[str, Any]:
        if self._workflow_registry is None:
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
            
            self._workflow_registry = workflows
        
        return self._workflow_registry

    def _load(self) -> Dict[str, Any]:
        """Carrega e retorna o conteúdo do arquivo YAML de workflows."""
        print(f"Carregando workflows do arquivo: {self.workflow_file_path}")
        try:
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"ERRO: Arquivo de workflow '{self.workflow_file_path}' não encontrado.")
            return {}
        except Exception as e:
            print(f"ERRO: Falha ao carregar ou parsear o arquivo '{self.workflow_file_path}': {e}")
            return {}
    
    def get_valid_analysis_types(self):
        if self._valid_analysis_types is None:
            workflow_registry = self.load_workflow_registry()
            valid_analysis_keys = {key: key for key in workflow_registry.keys()}
            self._valid_analysis_types = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)
        
        return self._valid_analysis_types
    
    def get_workflow_registry(self) -> Dict[str, Any]:
        return self.load_workflow_registry()
