import yaml
import enum
from typing import Dict, Any

class WorkflowRegistryService:
    """
    Carrega e gerencia o registro de workflows a partir de um arquivo YAML.
    Os dados são carregados uma única vez na inicialização para performance e fail-fast.
    """
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        """
        Inicializa o serviço carregando o arquivo de workflows imediatamente.
        """
        self.workflow_file_path = workflow_file_path
        # Carrega o registro e o enum uma única vez e os expõe como atributos públicos.
        self.registry: Dict[str, Any] = self._load_registry()
        self.analysis_types: enum.Enum = self._create_analysis_enum()

    def _load_registry(self) -> Dict[str, Any]:
        """
        Método privado para carregar o arquivo YAML de forma segura.
        """
        print(f"Carregando workflows do arquivo: {self.workflow_file_path}")
        try:
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                # yaml.safe_load é o padrão para arquivos de configuração de documento único.
                workflows = yaml.safe_load(f)
                # Garante que, se o arquivo estiver vazio, retornemos um dicionário.
                return workflows if isinstance(workflows, dict) else {}
        except FileNotFoundError:
            print(f"ERRO: Arquivo de workflow '{self.workflow_file_path}' não encontrado.")
            return {}
        except yaml.YAMLError as e:
            print(f"ERRO: Falha ao carregar ou parsear o arquivo '{self.workflow_file_path}': {e}")
            return {}

    def _create_analysis_enum(self) -> enum.Enum:
        """
        Cria dinamicamente o Enum com os tipos de análise válidos.
        """
        if not self.registry:
            # Se o registro estiver vazio, cria um enum com um valor padrão para evitar erros.
            return enum.Enum('ValidAnalysisTypes', {'NO_WORKFLOWS_LOADED': 'NO_WORKFLOWS_LOADED'})
            
        valid_analysis_keys = {key: key for key in self.registry.keys()}
        return enum.Enum('ValidAnalysisTypes', valid_analysis_keys)
