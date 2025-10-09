class ReportParserService:
    def parse_implementation_plan(self, report_text):
        tasks = []
        for line in report_text.splitlines():
            if 'EXCLUIR' in line or 'DELETE' in line:
                # Exemplo: | 3 | Serviços | EXCLUIR | `backend/app/deprecated_module.py` | ... |
                parts = [p.strip(' |`') for p in line.split('|')]
                if len(parts) >= 5:
                    step_number = int(parts[0])
                    layer = parts[1]
                    action = 'DELETE'
                    file_path = parts[3]
                    description = parts[4]
                    tasks.append(CodeTask(
                        id=f"task-{step_number}",
                        step_number=step_number,
                        layer=layer,
                        action=action,
                        file_path=file_path,
                        description=description,
                        dependencies=[],
                        estimated_tokens=0
                    ))
            # ... parsing padrão para outras ações ...
        return tasks
