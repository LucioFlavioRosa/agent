import re
import json
import time
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.agent_factory import AgentFactory
from tools.readers.azure_board_reader import AzureBoardReader
from services.azure_board_service import AzureBoardService

class RevisorBoardStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler=None, azure_board_service: AzureBoardService = None):
        self.job_handler = job_handler
        self.azure_board_service = azure_board_service

    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any],
                current_step_index: int, previous_step_result: Dict[str, Any],
                repo_reader, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        epic_id = job_info['data'].get('epic_id')
        organization = job_info['data'].get('organization')
        project = job_info['data'].get('project')
        if not epic_id:
            raise ValueError(f"[{job_id}] Parâmetro obrigatório 'epic_id' ausente em job_info['data'].")
        if not organization:
            raise ValueError(f"[{job_id}] Parâmetro obrigatório 'organization' ausente em job_info['data'].")
        if not project:
            raise ValueError(f"[{job_id}] Parâmetro obrigatório 'project' ausente em job_info['data'].")
        instrucoes_formatadas = job_info['data'].get('instrucoes_extras', '')
        instrucoes_formatadas += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR:\n"
        instrucoes_formatadas += json.dumps(previous_step_result, indent=2, ensure_ascii=False)
        observacoes_humanas = self.job_handler.get_approval_instructions(job_info) if self.job_handler else None
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
        agent_params.update({
            'epic_id': epic_id,
            'organization': organization,
            'project': project,
            'job_id': job_id,
            'projeto': job_info['data'].get('projeto'),
            'status_update': step['status_update']
        })
        # Passo 6: adicionar task_id se presente
        agent_params['task_id'] = job_info['data'].get('task_id')
        max_retries = 3
        if self.azure_board_service is None:
            self.azure_board_service = AzureBoardService(organization=organization, project=project)
        for attempt in range(max_retries):
            try:
                agente = AgentFactory.create_agent(
                    "revisor_board",
                    azure_board_service=self.azure_board_service,
                    llm_provider=llm_provider
                )
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
                    if previous_step_result and isinstance(previous_step_result, dict):
                        print(f"[{job_id}] A IA retornou resposta vazia ou inválida. Reutilizando resultado anterior.")
                        return previous_step_result
                    raise ValueError("IA retornou resposta vazia ou inválida e não há resultado anterior para usar.")
                result = json.loads(cleaned_string, strict=False)
                print(f"[{job_id}] JSON decodificado com sucesso na tentativa {attempt + 1}.")
                return result
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[{job_id}] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt + 1 == max_retries:
                    print(f"[{job_id}] ERRO: Máximo de tentativas atingido. Falhando o step.")
                    raise e
                time.sleep(2)
