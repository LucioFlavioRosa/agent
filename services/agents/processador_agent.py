import json
from typing import Dict, Any
from domain.interfaces.agent_interface import IAgent
from services.factories.agent_factory import AgentFactory

class ProcessadorAgent(IAgent):
    def __init__(self, repo_reader, llm_provider):
        self.repo_reader = repo_reader
        self.llm_provider = llm_provider
        self._agent = AgentFactory.create_agent("processador", repo_reader, llm_provider)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        job_id = kwargs.get('job_id')
        job_info = kwargs.get('job_info')
        current_step_index = kwargs.get('current_step_index')
        previous_step_result = kwargs.get('previous_step_result')
        step = kwargs.get('step')
        
        input_para_agente_final = {}
        
        if current_step_index == 0:
            instrucoes = job_info['data'].get('instrucoes_extras')
            input_para_agente_final = {"instrucoes_iniciais": instrucoes}
        else:
            input_para_agente_final = {"instrucoes_iniciais": previous_step_result}
        
        instrucoes_extras = job_info['data'].get('instrucoes_extras')
        observacoes_humanas = job_info['data'].get('instrucoes_extras_aprovacao')
        
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
                job_info['data']['instrucoes_extras_aprovacao'] = None
        
        agent_params = step.get('params', {}).copy()
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False),
            'model_name': step.get('model_name', job_info.get('data', {}).get('model_name')),
            'codigo': input_para_agente_final,
            'repository_type': job_info['data']['repository_type']
        })
        
        return self._agent.main(**agent_params)
    
    def get_agent_type(self) -> str:
        return "processador"