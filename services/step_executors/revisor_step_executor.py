import json
import re
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
        # Suporte a processamento incremental por batch
        if 'current_batch' in agent_params and agent_params['current_batch']:
            batch_steps = agent_params['current_batch']
            instrucoes_formatadas += "\n\n---\n\nExecutar APENAS os seguintes passos do relatório:\n"
            instrucoes_formatadas += json.dumps(batch_steps, indent=2, ensure_ascii=False)
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
        agente = AgentFactory.create_agent("revisor", repo_reader, llm_provider)
        agent_response = agente.main(**agent_params)
        
        raw_response_from_llm  = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        #cleaned_string = json_string.replace("```json", "").replace("```", "").strip()
        cleaned_string = None
        # Tenta encontrar ```json ... ```
        match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_response_from_llm)
        if match:
            cleaned_string = match.group(1).strip()
        else:
            # Se não encontrar, tenta pegar o conteúdo entre o primeiro '{' e o último '}'
            start = raw_response_from_llm.find('{')
            end = raw_response_from_llm.rfind('}')
            if start != -1 and end != -1:
                cleaned_string = raw_response_from_llm[start:end+1]

        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia ou inválida. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia ou inválida e não há resultado anterior para usar.")

        # 2. Tentar decodificar o JSON de forma segura
        try:
            return json.loads(cleaned_string, strict=False) # Adicionado strict=False por segurança
        except json.JSONDecodeError as e:
            print(f"[{job_id}] ERRO: Falha ao decodificar JSON mesmo após limpeza: {e}")
            print(f"[{job_id}] String que causou a falha (primeiros 500 caracteres):\n{cleaned_string[:500]}")
            # Lança a exceção novamente para que o workflow principal saiba que falhou
            raise e
