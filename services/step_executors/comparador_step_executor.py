import json
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.agent_factory import AgentFactory
from tools.readers.reader_geral import ReaderGeral

class ComparadorStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        repository_type = agent_params.get('repository_type')
        usuario_executor = agent_params.get('usuario_executor')
        repo_name_modernizado = agent_params.get('repo_name_modernizado')
        branch_name_modernizado = agent_params.get('branch_name_modernizado')
        repo_name_original = agent_params.get('repo_name_original')
        branch_name_original = agent_params.get('branch_name_original')
        tipo_analise = agent_params.get('tipo_analise')
        codigo_modernizado = repo_reader.read_repository(
            nome_repo=repo_name_modernizado,
            tipo_analise=tipo_analise,
            repository_type=repository_type,
            nome_branch=branch_name_modernizado,
            usuario_executor=usuario_executor
        )
        codigo_original = repo_reader.read_repository(
            nome_repo=repo_name_original,
            tipo_analise=tipo_analise,
            repository_type=repository_type,
            nome_branch=branch_name_original,
            usuario_executor=usuario_executor
        )
        agente = AgentFactory.create_agent("comparador", repo_reader, llm_provider)
        agent_response = agente.main(
            codigo_modernizado=codigo_modernizado,
            codigo_original=codigo_original,
            **agent_params
        )
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("```json", "").replace("```", "").strip()
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
        return json.loads(cleaned_string)
