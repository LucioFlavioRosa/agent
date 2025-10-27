from typing import List, Dict, Any
from services.task_parser_service import TaskParserService

class TaskDiscussionUpdaterService:
    def update_task_from_report(self, task_id: str, report: str, azure_board_service) -> Dict[str, Any]:
        if not report or not isinstance(report, str) or not report.strip():
            return {"error": "Relatório vazio ou inválido."}
        parser = TaskParserService()
        parsed_rows = parser.parse_tasks_from_markdown(report)
        if not parsed_rows or len(parsed_rows) == 0:
            return {"error": "Nenhuma linha encontrada na tabela do relatório."}
        discussion_entries = []
        for row in parsed_rows:
            categoria = row.get('Categoria') or row.get('categoria') or ''
            pergunta = row.get('Pergunta') or row.get('pergunta') or ''
            if categoria or pergunta:
                discussion_entries.append({"Categoria": categoria, "Pergunta": pergunta})
        if not discussion_entries:
            return {"error": "Nenhuma entrada válida de Categoria/Pergunta encontrada."}
        result = azure_board_service.update_task_discussion(task_id, discussion_entries)
        return result
