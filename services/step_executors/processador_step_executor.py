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
            'codigo': previous_step_result,
            'repositorio': job_info['data']['repo_name'],
            'nome_branch': job_info['data']['branch_name'],
            'repository_type': job_info['data']['repository_type']
        })
        
        # Passo 11: Propagar retornar_lista_arquivos
        agent_params['retornar_lista_arquivos'] = agent_params.get('retornar_lista_arquivos', False)
        # Se previous_step_result contém lista_arquivos, propagar também
        if isinstance(previous_step_result, dict) and 'lista_arquivos' in previous_step_result:
            agent_params['lista_arquivos'] = previous_step_result['lista_arquivos']
        
        agente = AgentFactory.create_agent("processador", None, llm_provider)
        agent_response = agente.main(**agent_params)
        
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("```json", "").replace("```", "").strip()
        
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
        
        return json.loads(cleaned_string)
