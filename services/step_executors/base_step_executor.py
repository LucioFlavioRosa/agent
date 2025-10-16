from abc import ABC, abstractmethod
from typing import Dict, Any
from tools.readers.reader_geral import ReaderGeral

class BaseStepExecutor(ABC):
    @abstractmethod
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        pass