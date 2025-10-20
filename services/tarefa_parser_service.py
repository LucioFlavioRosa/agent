import re
from typing import List
from models import TarefaCard

class TarefaParserService:
    @staticmethod
    def parse_tarefas_from_report(report_text: str, epico_id: str) -> List[TarefaCard]:
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
        tarefas = []
        for line in data_lines:
            if not line.startswith('|') or line == separator:
                continue
            columns = [col.strip() for col in line.strip('|').split('|')]
            if len(columns) < 6:
                continue
            tarefa = TarefaCard(
                id=columns[0],
                titulo_tarefa=columns[1],
                descricao_tarefa=columns[2],
                epico_id=epico_id,
                estimativa_tempo=columns[4],
                criterios_aceite=columns[5]
            )
            tarefas.append(tarefa)
        return tarefas
