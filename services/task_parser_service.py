import re
from typing import List, Dict, Any

class TaskParserService:
    def parse_tasks_from_markdown(self, markdown_table: str) -> List[Dict[str, Any]]:
        try:
            print(f"[TaskParserService-DEBUG] Iniciando parsing. Tamanho do markdown: {len(markdown_table)} caracteres")
            lines = [line for line in markdown_table.splitlines() if line.strip()]
            header = None
            tasks = []
            for idx, line in enumerate(lines):
                if line.startswith('|') and line.endswith('|'):
                    cols = [col.strip() for col in line.strip('|').split('|')]
                    if not header:
                        header = [h.lower().strip() for h in cols]
                        print(f"[TaskParserService-DEBUG] Cabeçalho identificado: {header}")
                        continue
                    if len(cols) != len(header):
                        print(f"[TaskParserService-DEBUG] Linha ignorada por tamanho diferente do header. Linha {idx}: {cols}")
                        continue
                    task = {}
                    for col_idx, col in enumerate(cols):
                        key = header[col_idx]
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
                        print(f"[TaskParserService-DEBUG] Tarefa parseada: {task}")
                        tasks.append(task)
            print(f"[TaskParserService-DEBUG] Parsing concluído. Total de tarefas parseadas: {len(tasks)}")
            if len(tasks) == 0:
                print(f"[TaskParserService-WARNING] Nenhuma tarefa foi parseada da tabela Markdown. Verifique o formato da tabela.")
            return tasks
        except Exception as e:
            print(f"[TaskParserService-ERROR] Erro ao fazer parsing do markdown: {str(e)}")
            return []
