import re
import json
import time

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
        max_retries = 3
        for attempt in range(max_retries):
            try:
                agente = AgentFactory.create_agent("revisor", repo_reader, llm_provider)
                agent_response = agente.main(**agent_params)
                raw_response_from_llm = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')

                cleaned_string = None
                match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_response_from_llm)
                if match:
                    cleaned_string = match.group(1).strip()
                else:
                    start = raw_response_from_llm.find('{')
                    end = raw_response_from_llm.rfind('}')
                    if start != -1 and end != -1:
                        cleaned_string = raw_response_from_llm[start:end+1]

                if not cleaned_string:
                    # Se não encontrar JSON, não adianta tentar de novo. Usa o resultado anterior ou falha.
                    if previous_step_result and isinstance(previous_step_result, dict):
                        print(f"[{job_id}] A IA retornou resposta vazia ou inválida. Reutilizando resultado anterior.")
                        return previous_step_result
                    raise ValueError("IA retornou resposta vazia ou inválida e não há resultado anterior para usar.")

                result = json.loads(cleaned_string, strict=False)
                print(f"[{job_id}] JSON decodificado com sucesso na tentativa {attempt + 1}.")
                return result

            except (json.JSONDecodeError, ValueError) as e:
                # Se o try falhar, o except é ativado.
                print(f"[{job_id}] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt + 1 == max_retries:
                    # Se esta foi a última tentativa, desiste e lança o erro.
                    print(f"[{job_id}] ERRO: Máximo de tentativas atingido. Falhando o step.")
                    raise e
                    
                time.sleep(2)
