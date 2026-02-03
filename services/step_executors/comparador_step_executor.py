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
            'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
            'repository_type': job_info['data']['repository_type'],
            'job_id': job_id,
            'projeto': job_info['data']['projeto'],
            'status_update': step['status_update']
        })
        # Removido: agent_params['usar_rag']
        # Removido import e uso de AgentFactory conforme remoção do arquivo
        raise NotImplementedError("AgentFactory foi removido do projeto. Adapte a lógica de instanciacao do agente comparador conforme novo padrão.")
