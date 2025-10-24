import re
from typing import List, Dict, Any

class TaskParserService:
    def parse_tasks_from_markdown(self, markdown_table: str) -> List[Dict[str, Any]]:
        lines = [line for line in markdown_table.splitlines() if line.strip()]
        header = None
        tasks = []
        for line in lines:
            if line.startswith('|') and line.endswith('|'):
                cols = [col.strip() for col in line.strip('|').split('|')]
                if not header:
                    header = [h.lower().strip() for h in cols]
                    continue
                if len(cols) != len(header):
                    continue
                task = {}
                for idx, col in enumerate(cols):
                    key = header[idx]
                    if key in ['id', 'passos', 'passo', 'passo #']:
                        task['id'] = col
                    elif key in ['título', 'titulo', 'title']:
                        task['titulo'] = col
                    elif key in ['descrição', 'descricao', 'description']:
                        task['descricao'] = col
                    elif key in ['tipo', 'type']:
                        task['tipo'] = col
                    elif key in ['critérios de aceite', 'criterios de aceite', 'acceptance criteria']:
                        task['criterios_aceite'] = col.replace('<br>', '\n').replace('- ', '\n- ').strip()
                    elif key in ['perfis sugeridos', 'profiles']:
                        task['perfis_sugeridos'] = col
                    elif key in ['estimativa (sp)', 'estimativa', 'story points']:
                        task['estimativa_sp'] = col
                if task:
                    tasks.append(task)
        print(f"[TaskParserService] [DEBUG] Total de tarefas parseadas: {len(tasks)}")
        for t in tasks:
            print(f"[TaskParserService] [DEBUG] Tarefa: {t}")
        return tasks
