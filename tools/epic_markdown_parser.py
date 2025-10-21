import re
from typing import List, Dict, Any
from domain.interfaces.epic_parser_interface import IEpicParser

class EpicMarkdownParser(IEpicParser):
    def parse_epic_table(self, markdown_table: str) -> List[Dict[str, Any]]:
        lines = markdown_table.strip().split('\n')
        header_found = False
        header = []
        epics = []
        for line in lines:
            if not header_found and line.startswith('|') and 'Passo' in line:
                header = [h.strip() for h in line.split('|')[1:-1]]
                header_found = True
                continue
            if header_found and line.startswith('|') and not line.startswith('|---'):
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) != len(header):
                    continue
                epics.append({
                    'passo': cols[0],
                    'epico': cols[1],
                    'objetivo_negocio': cols[2],
                    'criterios_aceite': cols[3],
                    'perfis_envolvidos': cols[4],
                    'estimativa_esforco': cols[5]
                })
        return epics
