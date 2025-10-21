from typing import List, Dict, Any

class IEpicParser:
    def parse_epic_table(self, markdown_table: str) -> List[Dict[str, Any]]:
        raise NotImplementedError