from typing import Dict, Any
from domain.interfaces.agent_interface import IAgent
from services.factories.agent_factory import AgentFactory

class RevisorAgent(IAgent):
    def __init__(self, repo_reader, llm_provider):
        self.repo_reader = repo_reader
        self.llm_provider = llm_provider
        self._agent = AgentFactory.create_agent("revisor", repo_reader, llm_provider)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        job_id = kwargs.get('job_id')
        job_info = kwargs.get('job_info')
        current_step_index = kwargs.get('current_step_index')
        previous_step_result = kwargs.get('previous_step_result')
        step = kwargs.get('step')
        
        instrucoes = job_info['data'].get('instrucoes_extras', '')
        
        if current_step_index > 0:
            instrucoes += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR:\n"
            instrucoes += str(previous_step_result)
        
        observacoes_humanas = job_info['data'].get('instrucoes_extras_aprovacao')
        if observacoes_humanas:
            instrucoes += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"
            print(f"[{job_id}] Aplicando instruções extras de aprovação na etapa {current_step_index}: {observacoes_humanas[:100]}...")
            job_info['data']['instrucoes_extras_aprovacao'] = None
        
        agent_params = step.get('params', {}).copy()
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False),
            'model_name': step.get('model_name', job_info.get('data', {}).get('model_name')),
            'repositorio': job_info['data']['repo_name'],
            'nome_branch': job_info['data']['branch_name'],
            'instrucoes_extras': instrucoes,
            'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
            'repository_type': job_info['data']['repository_type'],
            'job_id': job_id,
            'projeto': job_info['data']['projeto'],
            'status_update': step['status_update']
        })
        
        return self._agent.main(**agent_params)
    
    def get_agent_type(self) -> str:
        return "revisor"