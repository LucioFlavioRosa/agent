from mcp_server_fastapi import JobFields
class DataFormatter:
    def __init__(self, changeset_filler=None):
        self.changeset_filler = changeset_filler
    def extract_workflow_results(self, job_info, workflow, final_result):
        resultado_agrupamento = final_result.get('final_result') if isinstance(final_result, dict) else None
        resultado_refatoracao = final_result.get('penultimate_result') if isinstance(final_result, dict) else None
        return resultado_agrupamento, resultado_refatoracao
    def populate_changeset_data(self, resultado_agrupamento, resultado_refatoracao):
        if self.changeset_filler:
            return self.changeset_filler.fill(resultado_agrupamento, resultado_refatoracao)
        return resultado_agrupamento
    def format_final_data(self, dados_preenchidos):
        return dados_preenchidos
