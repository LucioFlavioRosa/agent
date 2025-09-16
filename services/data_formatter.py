from typing import Dict, Any
from tools.preenchimento import ChangesetFiller

class DataFormatter:
    def __init__(self, changeset_filler: ChangesetFiller = None):
        self.changeset_filler = changeset_filler or ChangesetFiller()
    
    def populate_changeset_data(self, resultado_agrupamento: Dict[str, Any], resultado_refatoracao: Dict[str, Any]) -> Dict[str, Any]:
        return self.changeset_filler.main(
            json_agrupado=resultado_agrupamento,
            json_inicial=resultado_refatoracao
        )
    
    def format_final_data(self, dados_preenchidos: Dict[str, Any]) -> Dict[str, Any]:
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}

        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral":
                continue
            dados_finais_formatados["grupos"].append({
                "branch_sugerida": nome_grupo, 
                "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), 
                "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), 
                "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])
            })

        return dados_finais_formatados
    
    def extract_workflow_results(self, job_info: Dict[str, Any], workflow: Dict[str, Any], final_result: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        workflow_steps = workflow.get("steps", [])
        num_total_steps = len(workflow_steps)

        resultado_agrupamento = final_result
        resultado_refatoracao = {}

        if num_total_steps >= 2:
            penultimate_step_index = num_total_steps - 2
            resultado_refatoracao = job_info['data'].get(f'step_{penultimate_step_index}_result', {})
        elif num_total_steps == 1:
            resultado_refatoracao = final_result
        
        return resultado_agrupamento, resultado_refatoracao