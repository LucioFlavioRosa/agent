import re
from typing import List, Dict, Any

class TaskParserService:
    def parse_tasks_from_markdown(self, markdown_table: str) -> List[Dict[str, Any]]:
        """
        Parseia uma tabela Markdown de tarefas e retorna uma lista de dicionários.
        Espera colunas como: título, descricao, criterios_aceite, perfis_sugeridos, estimativa_sp
        """
        lines = [line for line in markdown_table.strip().splitlines() if line.strip() and not line.strip().startswith('|---')]
        if len(lines) < 2:
            return []
        header_line = lines[0].strip()
        if header_line.startswith('|'):
            header_line = header_line[1:]
        if header_line.endswith('|'):
            header_line = header_line[:-1]
        header = [h.strip().lower() for h in header_line.split('|')]
        tasks = []
        for line in lines[1:]:
            line = line.strip()
            if not line.startswith('|'):
                continue
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
            cols = [col.strip() for col in line.split('|')]
            if len(cols) == len(header):
                try:
                    task = dict(zip(header, cols))
                    # Normaliza os campos esperados
                    parsed_task = {
                        'titulo': task.get('título') or task.get('titulo') or '',
                        'descricao': task.get('descrição') or task.get('descricao') or '',
                        'criterios_aceite': task.get('critérios de aceite') or task.get('criterios de aceite') or '',
                        'perfis_sugeridos': task.get('perfis sugeridos') or '',
                        'estimativa_sp': task.get('estimativa (sp)') or task.get('estimativa_sp') or ''
                    }
                    tasks.append(parsed_task)
                except Exception:
                    continue
        return tasks
