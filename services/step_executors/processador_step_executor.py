import json
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.agent_factory import AgentFactory
from tools.readers.reader_geral import ReaderGeral

class ProcessadorStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        
        input_para_agente_final = {}
        
        if current_step_index == 0:
            instrucoes = job_info['data'].get('instrucoes_extras')
            input_para_agente_final = {"instrucoes_iniciais": instrucoes}
        else:
            input_para_agente_final = {"instrucoes_iniciais": previous_step_result}
        
        instrucoes_extras = job_info['data'].get('instrucoes_extras')
        observacoes_humanas = self.job_handler.get_approval_instructions(job_info)
        
        if instrucoes_extras or observacoes_humanas:
            if isinstance(input_para_agente_final.get('instrucoes_iniciais'), dict):
                if instrucoes_extras:
                    input_para_agente_final['instrucoes_iniciais']['instrucoes_extras'] = instrucoes_extras
                if observacoes_humanas:
                    input_para_agente_final['instrucoes_iniciais']['observacoes_aprovacao'] = observacoes_humanas
            elif isinstance(input_para_agente_final.get('instrucoes_iniciais'), str):
                if instrucoes_extras:
                    input_para_agente_final['instrucoes_iniciais'] += f"\n\n---\n\nINSTRUÇÕES EXTRAS DO USUÁRIO:\n{instrucoes_extras}"
                if observacoes_humanas:
                    input_para_agente_final['instrucoes_iniciais'] += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"
            else:
                if instrucoes_extras:
                    input_para_agente_final['instrucoes_extras'] = instrucoes_extras
                if observacoes_humanas:
                    input_para_agente_final['observacoes_aprovacao'] = observacoes_humanas
            
            if observacoes_humanas:
                print(f"[{job_id}] Aplicando instruções extras de aprovação no processador da etapa {current_step_index}: {observacoes_humanas[:100]}...")
                self.job_handler.clear_approval_instructions(job_info)
                self.job_handler.update_job(job_id, job_info)
        
        agent_params['codigo'] = input_para_agente_final
        
        agente = AgentFactory.create_agent("processador", repo_reader, llm_provider)
        agent_response = agente.main(**agent_params)
        
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("```json", "").replace("```", "").strip()
        
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
        
        return json.loads(cleaned_string)
