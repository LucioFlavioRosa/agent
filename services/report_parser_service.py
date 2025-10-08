import re
from typing import List
from domain.models.incremental_change_models import CodeTask

class ReportParserService:
    def parse_implementation_plan(self, report_text: str) -> List[CodeTask]:
        tasks = []
        table_pattern = re.compile(r'\| Passo # \|.*?\| Justificativa.*?\|', re.DOTALL)
        table_match = table_pattern.search(report_text)
        if not table_match:
            return []
        table_start = table_match.start()
        lines = report_text[table_start:].split('\n')
        for line in lines:
            if re.match(r'^\|\s*\d+\s*\|', line):
                cols = [col.strip() for col in line.split('|')[1:-1]]
                if len(cols) < 4:
                    continue
                step_number = int(cols[0])
                layer = cols[1]
                action_detail = cols[2]
                description = action_detail
                action = None
                file_path = None
                action_match = re.search(r'\*\*(CRIAR|MODIFICAR|ADICIONAR)\*\*', action_detail)
                if action_match:
                    action = action_match.group(1)
                file_match = re.search(r'`([^`]+)`', action_detail)
                if file_match:
                    file_path = file_match.group(1)
                if action in ['CRIAR', 'MODIFICAR', 'ADICIONAR'] and file_path:
                    estimated_tokens = int(len(description) / 4)
                    task_id = f"step_{step_number}_{action.lower()}_{file_path.replace('/', '_').replace('.', '_')}"
                    task = CodeTask(
                        id=task_id,
                        step_number=step_number,
                        layer=layer,
                        action=action,
                        file_path=file_path,
                        description=description,
                        dependencies=[],
                        estimated_tokens=estimated_tokens,
                        status='pending'
                    )
                    tasks.append(task)
        return tasks

    def extract_file_dependencies(self, task: CodeTask) -> List[str]:
        dependencies = []
        dep_patterns = [
            r'Injetar [`"]?([\w/\.]+)[`"]?',
            r'Integrar com [`"]?([\w/\.]+)[`"]?',
            r'Usar [`"]?([\w/\.]+)[`"]?',
            r'Implementar [`"]?([\w/\.]+)[`"]?'
        ]
        for pattern in dep_patterns:
            matches = re.findall(pattern, task.description)
            for match in matches:
                dependencies.append(match)
        return dependencies
