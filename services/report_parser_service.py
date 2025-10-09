class ReportParserService:
    def parse_implementation_plan(self, report_text):
        # Parseia o relatório e identifica ações de exclusão
        tarefas = []
        for linha in report_text.splitlines():
            if 'EXCLUIR' in linha or 'DELETE' in linha:
                partes = linha.split('|')
                if len(partes) >= 5:
                    file_path = partes[3].strip().strip('`')
                    description = partes[4].strip()
                    tarefas.append({
                        'action': 'DELETE',
                        'file_path': file_path,
                        'description': description
                    })
            # ... lógica para outras ações ...
        return tarefas
