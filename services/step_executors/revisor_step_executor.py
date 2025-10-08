import json
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.agent_factory import AgentFactory
from tools.readers.reader_geral import ReaderGeral

class RevisorStepExecutor(BaseStepExecutor):
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
        
        if 'repositorio' not in agent_params:
            agent_params['repositorio'] = job_info['data']['repo_name']
        if 'nome_branch' not in agent_params:
            agent_params['nome_branch'] = job_info['data']['branch_name']
        
        agent_params.update({
            'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
            'repository_type': job_info['data']['repository_type'],
            'job_id': job_id,
            'projeto': job_info['data']['projeto'],
            'status_update': step['status_update']
        })
        
        agent_params['retornar_lista_arquivos'] = agent_params.get('retornar_lista_arquivos', False)
        agent_params['modo_adicao_incremental'] = agent_params.get('modo_adicao_incremental', False)
        # Se o revisor precisar ler o repositório, propague usuario_executor:
        # usuario_executor = agent_params.get('usuario_executor')
        # repositorio = agent_params.get('repositorio')
        # tipo_analise = agent_params.get('tipo_analise')
        # nome_branch = agent_params.get('nome_branch')
        # arquivos_especificos = agent_params.get('arquivos_especificos')
        # retornar_lista_arquivos = agent_params.get('retornar_lista_arquivos', False)
        # codigo_base = repo_reader.read_repository(
        #     nome_repo=repositorio,
        #     tipo_analise=tipo_analise,
        #     repository_type=agent_params.get('repository_type'),
        #     nome_branch=nome_branch,
        #     arquivos_especificos=arquivos_especificos,
        #     retornar_lista_arquivos=retornar_lista_arquivos,
        #     usuario_executor=usuario_executor
        # )
        agente = AgentFactory.create_agent("revisor", repo_reader, llm_provider)
        agent_response = agente.main(**agent_params)
        
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("", "").replace("", "").strip()
        
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
        
        return json.loads(cleaned_string)
