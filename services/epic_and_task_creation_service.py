class EpicAndTaskCreationService:
    def __init__(self, azure_boards_service, epico_parser_service, tarefa_parser_service):
        self.azure_boards_service = azure_boards_service
        self.epico_parser_service = epico_parser_service
        self.tarefa_parser_service = tarefa_parser_service

    def create_epics_and_tasks_from_report(self, job_id, job_info, analysis_report, organization_url, project_name):
        epicos = self.epico_parser_service.parse_epicos_from_report(analysis_report)
        instrucoes_extras = job_info['data'].get('instrucoes_extras')
        epicos_aprovados_nomes = None
        if instrucoes_extras:
            import re, json
            ids_regex = re.findall(r'\bE\d{2,}\b', instrucoes_extras)
            titulos_regex = re.findall(r'epico com titulo ([\w\s\-]+)', instrucoes_extras, re.IGNORECASE)
            ids_text = re.findall(r'epico com id ([\w\d]+)', instrucoes_extras, re.IGNORECASE)
            epicos_aprovados_nomes = list(set(ids_regex + ids_text + titulos_regex))
            if not epicos_aprovados_nomes:
                try:
                    parsed = json.loads(instrucoes_extras)
                    if isinstance(parsed, list):
                        epicos_aprovados_nomes = [str(e) for e in parsed]
                    elif isinstance(parsed, dict) and 'epicos_aprovados' in parsed:
                        epicos_aprovados_nomes = [str(e) for e in parsed['epicos_aprovados']]
                    else:
                        epicos_aprovados_nomes = [s.strip() for s in instrucoes_extras.split(',') if s.strip()]
                except Exception:
                    epicos_aprovados_nomes = [s.strip() for s in instrucoes_extras.split(',') if s.strip()]
        epicos_a_processar = epicos
        if epicos_aprovados_nomes:
            epicos_a_processar = [e for e in epicos if (e.id in epicos_aprovados_nomes or e.titulo in epicos_aprovados_nomes)]
        cards_criados = []
        tarefas_criadas = []
        tarefas_creation_errors = []
        tarefas_parsing_errors = []
        for epico in epicos_a_processar:
            card_result = self.azure_boards_service.criar_card_epico(epico)
            cards_criados.append(card_result)
            epic_id = card_result.get('id')
            tarefas = None
            try:
                tarefas = self.tarefa_parser_service.parse_tarefas_from_report(analysis_report, epico_id=epico.id, epico_nome=epico.titulo)
                if not tarefas:
                    tarefas = self.tarefa_parser_service.parse_tarefas_from_report(analysis_report, epico_id=None, epico_nome=epico.titulo)
                if not tarefas:
                    tarefas_parsing_errors.append({
                        'epico_id': epico.id,
                        'epico_nome': epico.titulo,
                        'analysis_report': analysis_report
                    })
            except Exception as e:
                tarefas_parsing_errors.append({
                    'epico_id': epico.id,
                    'epico_nome': epico.titulo,
                    'error': str(e),
                    'analysis_report': analysis_report
                })
                tarefas = []
            if tarefas:
                tarefas_result = self.azure_boards_service.criar_multiplas_tarefas(tarefas, epico_nome=epico.titulo, epic_id=epic_id)
                tarefas_criadas.extend(tarefas_result)
                tarefas_creation_errors.extend([r for r in tarefas_result if r.get('erro')])
        return {
            'cards_criados': cards_criados,
            'tarefas_criadas': tarefas_criadas,
            'tarefas_creation_errors': tarefas_creation_errors,
            'tarefas_parsing_errors': tarefas_parsing_errors
        }
