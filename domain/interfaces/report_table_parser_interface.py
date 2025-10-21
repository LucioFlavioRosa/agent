from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class IReportTableParser(ABC):
    @abstractmethod
    def parse_report_table(self, report_text: str, transcricao_reuniao: Optional[str] = None) -> List[Dict]:
        pass

    @abstractmethod
    def parse_epicos_table(self, report_text: str) -> List[Dict]:
        pass
