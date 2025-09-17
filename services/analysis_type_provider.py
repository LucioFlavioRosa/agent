import enum
from typing import Dict, Any

class AnalysisTypeProvider:
    def __init__(self):
        self._valid_analysis_types = None
    
    def get_valid_analysis_types(self, workflow_registry: Dict[str, Any]):
        if self._valid_analysis_types is None:
            valid_analysis_keys = {key: key for key in workflow_registry.keys()}
            self._valid_analysis_types = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)
        
        return self._valid_analysis_types