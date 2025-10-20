import re
from typing import List
from models import EpicoCard

class EpicoParserService:
    @staticmethod
    def parse_epicos_from_report(report_text: str) -> List[EpicoCard]:
        if not report_text or '| ID |' not in report_text:
            return []
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        table_start = None
        for idx, line in enumerate(lines):
            if line.startswith('| ID |'):
                table_start = idx
                break
        if table_start is None:
            return []
        header = lines[table_start]
        separator = lines[table_start + 1] if table_start + 1 < len(lines) else ''
        data_lines = lines[table_start + 2:]
        epicos = []
        for line in data_lines:
            if not line.startswith('|') or line == separator:
                continue
            columns = [col.strip() for col in line.strip('|').split('|')]
            if len(columns) < 6:
                continue
            epico = EpicoCard(
                id=columns[0],
                titulo=columns[1],
                objetivo_negocio=columns[2],
                criterios_aceite=columns[3],
                perfis_envolvidos=columns[4],
                estimativa_esforco=columns[5]
            )
            epicos.append(epico)
        return epicos
