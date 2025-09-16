from abc import ABC, abstractmethod
from typing import Dict, Any

class IAgent(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_agent_type(self) -> str:
        pass