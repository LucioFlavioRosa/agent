from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from tools.readers.reader_geral import ReaderGeral

class BaseStepExecutor(ABC):
    @abstractmethod
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any],
                access_token: str, access_token_original: Optional[str] = None) -> Dict[str, Any]:
        pass