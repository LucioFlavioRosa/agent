import re
import json
import time

from typing import Dict, Any

from agents.agente_revisor import AgenteRevisor
from services.step_executors.base_step_executor import BaseStepExecutor
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
        if 'current_batch' in agent_params and agent_params['current_batch']:
            batch_steps = agent_params['current_batch']
            instrucoes_formatadas += "\n\n---\n\nExecutar APENAS os seguintes passos do relatório:\n"
            instrucoes_formatadas += json.dumps(batch_steps, indent=2, ensure_ascii=False)
        agent_params['instrucoes_extras'] = instrucoes_formatadas
        agent_params['repositorio'] = job_info['data']['repo_name']
        agent_params['nome_branch'] = job_info['data']['branch_name']
        agent_params.update({
            'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
            'repository_type': job_info['data']['repository_type'],
            'job_id': job_id,
            'projeto': job_info['data']['projeto'],
            'analysis_name': job_info['data'].get('analysis_name'),
            'gerar_relatorio_apenas': job_info['data'].get('gerar_relatorio_apenas'),
            'retornar_lista_arquivos': job_info['data'].get('retornar_lista_arquivos', False),
            'usuario_executor': job_info['data'].get('usuario_executor'),
            'status_update': step['status_update']
        })
        # Passo 4: garantir que o parâmetro tipo_analise seja extraído corretamente e passado como analysis_type
        if 'params' in step and 'tipo_analise' in step['params']:
            agent_params['analysis_type'] = step['params']['tipo_analise']
        max_retries = 3
        for attempt in range(max_retries):
            try:
                agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
                return agente.executar(job_id, agent_params)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[{job_id}] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt + 1 == max_retries:
                    print(f"[{job_id}] ERRO: Máximo de tentativas atingido. Falhando o step.")
                    raise e
                time.sleep(2)
