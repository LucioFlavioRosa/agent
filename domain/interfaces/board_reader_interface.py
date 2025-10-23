from abc import ABC, abstractmethod
from typing import Dict, Any

class IBoardReader(ABC):
    @abstractmethod
    def read_epic(self, epic_id: str, organization: str, project: str) -> Dict[str, Any]:
        pass
