from abc import ABC, abstractmethod
from typing import Dict, Any
from tools.readers.reader_geral import ReaderGeral

class IStepStrategy(ABC):
    @abstractmethod
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                    current_step_index: int, previous_step_result: Dict[str, Any], 
                    repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        pass