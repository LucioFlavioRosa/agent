class ReportParserService:
    def parse_implementation_plan(self, report_text):
        tasks = []
        # parsing simplificado para exemplo
        lines = report_text.splitlines()
        for line in lines:
            if 'Ação:' in line or 'Action:' in line:
                if 'EXCLUIR' in line or 'DELETE' in line:
                    file_path = line.split()[-1].strip('`')
                    tasks.append({
                        'action': 'DELETE',
                        'file_path': file_path
                    })
                # outros casos para criar/modificar
        return tasks
