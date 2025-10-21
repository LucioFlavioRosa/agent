import re
import json
from typing import List, Optional, Dict, Any
from models import TarefaCard

class TarefaParserService:
    @staticmethod
    def parse_tarefas_from_report(report, epico_id: Optional[str] = None, epico_nome: Optional[str] = None) -> List[TarefaCard]:
        tarefas = []
        # Se report for dict e tiver lista_de_tarefas, parse JSON
        if isinstance(report, dict) and 'lista_de_tarefas' in report:
            for t in report['lista_de_tarefas']:
                tarefas.append(TarefaCard(
                    id=t.get('id', ''),
                    titulo_tarefa=t.get('titulo', ''),
                    descricao_tarefa=t.get('descricao', ''),
                    epico_id=epico_id or '',
                    estimativa_tempo=str(t.get('estimativa_sp', '')),
                    criterios_aceite=t.get('criterios_de_aceite', ''),
                    epico_nome=epico_nome
                ))
            return tarefas
        # Se report for string, tentar JSON
        if isinstance(report, str):
            try:
                data = json.loads(report)
                if isinstance(data, dict) and 'lista_de_tarefas' in data:
                    for t in data['lista_de_tarefas']:
                        tarefas.append(TarefaCard(
                            id=t.get('id', ''),
                            titulo_tarefa=t.get('titulo', ''),
                            descricao_tarefa=t.get('descricao', ''),
                            epico_id=epico_id or '',
                            estimativa_tempo=str(t.get('estimativa_sp', '')),
                            criterios_aceite=t.get('criterios_de_aceite', ''),
                            epico_nome=epico_nome
                        ))
                    return tarefas
            except Exception:
                pass
        # Fallback: parser Markdown
        if isinstance(report, str) and '| id |' in report.lower():
            lines = [line.strip() for line in report.splitlines() if line.strip()]
            table_start = None
            for idx, line in enumerate(lines):
                if line.lower().startswith('| id |'):
                    table_start = idx
                    break
            if table_start is None:
                return tarefas
            separator = lines[table_start + 1] if table_start + 1 < len(lines) else ''
            data_lines = lines[table_start + 2:]
            for line in data_lines:
                if not line.startswith('|') or line == separator:
                    continue
                columns = [col.strip() for col in line.strip('|').split('|')]
                if len(columns) < 6:
                    continue
                tarefas.append(TarefaCard(
                    id=columns[0],
                    titulo_tarefa=columns[1],
                    descricao_tarefa=columns[2],
                    epico_id=epico_id or '',
                    estimativa_tempo=columns[4],
                    criterios_aceite=columns[5],
                    epico_nome=epico_nome
                ))
        return tarefas
