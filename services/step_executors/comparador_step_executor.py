import json
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from tools.readers.reader_geral import ReaderGeral

class ComparadorStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        instrucoes_formatadas = job_info['data'].get('instrucoes_extras', '')
        instrucoes_formatadas += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR:\n"
        instrucoes_formatadas += json.dumps(previous_step_result, indent=2, ensure_ascii=False)

        observacoes_humanas = self.job_handler.get_approval_instructions(job_info)
        if observacoes_humanas:
            instrucoes_formatadas += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"
            print(f"[{job_id}] Aplicando instruções extras de aprovação na etapa {current_step_index}: {observacoes_humanas[:100]}...")
            self.job_handler.clear_approval_instructions(job_info)
            self.job_handler.update_job(job_id, job_info)

        agent_params['instrucoes_extras'] = instrucoes_formatadas
        agent_params.update({
            'repo_name': job_info['data']['repo_name'],
            'branch_name': job_info['data']['branch_name'],
            'repository_type': job_info['data']['repository_type'],
            'analysis_type': job_info['data']['analysis_type'],
            'projeto': job_info['data']['projeto'],
            'analysis_name': job_info['data'].get('analysis_name'),
            'gerar_relatorio_apenas': job_info['data'].get('gerar_relatorio_apenas'),
            'retornar_lista_arquivos': job_info['data'].get('retornar_lista_arquivos', False),
            'usuario_executor': job_info['data'].get('usuario_executor'),
            'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
            'job_id': job_id,
            'status_update': step['status_update']
        })
        raise NotImplementedError("AgentFactory foi removido do projeto. Adapte a lógica de instanciacao do agente comparador conforme novo padrão.")
