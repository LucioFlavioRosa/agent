from typing import Dict, Any
from services.workflow_registry_loader import WorkflowRegistryLoader
from services.analysis_type_provider import AnalysisTypeProvider

class WorkflowRegistryService:
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        self._workflow_registry = None
        self._loader = WorkflowRegistryLoader(workflow_file_path)
        self._analysis_type_provider = AnalysisTypeProvider()
    
    def load_workflow_registry(self) -> Dict[str, Any]:
        if self._workflow_registry is None:
            self._workflow_registry = self._loader.load_workflows()
        
        return self._workflow_registry
    
    def get_valid_analysis_types(self):
        workflow_registry = self.load_workflow_registry()
        return self._analysis_type_provider.get_valid_analysis_types(workflow_registry)
    
    def get_workflow_registry(self) -> Dict[str, Any]:
        return self.load_workflow_registry()