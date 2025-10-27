from typing import List, Dict, Any
from services.task_discussion_parser_service import TaskDiscussionParserService

class TaskDiscussionUpdaterService:
    def update_task_from_report(self, task_id: str, report: str, azure_board_service) -> Dict[str, Any]:
        if not report or not isinstance(report, str) or not report.strip():
            return {"error": "Relatório vazio ou inválido."}
        parsed_entries = TaskDiscussionParserService.parse_discussion_entries_from_markdown(report)
        if not parsed_entries or len(parsed_entries) == 0:
            return {"error": "Nenhuma entrada válida de Categoria/Pergunta encontrada."}
        discussion_entries = []
        for entry in parsed_entries:
            categoria = entry.get('categoria', '')
            pergunta = entry.get('pergunta', '')
            if categoria or pergunta:
                discussion_entries.append({"Categoria": categoria, "Pergunta": pergunta})
        if not discussion_entries:
            return {"error": "Nenhuma entrada válida de Categoria/Pergunta encontrada."}
        result = azure_board_service.update_task_discussion(task_id, discussion_entries)
        return result
