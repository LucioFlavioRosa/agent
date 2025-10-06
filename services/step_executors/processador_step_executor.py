from typing import Dict, Any
from agents.agente_processador import AgenteProcessador
from domain.interfaces.llm_provider_interface import ILLMProvider

class ProcessadorStepExecutor:
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], agent_params: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        print(f"[ProcessadorStepExecutor] Chamando agente com job_id: {job_id}")
        agente = AgenteProcessador(self.llm_provider)
        # Garante que job_id está presente nos parâmetros
        agent_params = dict(agent_params)
        agent_params['job_id'] = job_id
        return agente.main(
            tipo_analise=agent_params.get('tipo_analise'),
            codigo=agent_params.get('codigo'),
            repository_type=agent_params.get('repository_type'),
            repositorio=agent_params.get('repositorio'),
            nome_branch=agent_params.get('nome_branch'),
            instrucoes_extras=agent_params.get('instrucoes_extras', ""),
            usar_rag=agent_params.get('usar_rag', False),
            model_name=agent_params.get('model_name'),
            max_token_out=agent_params.get('max_token_out', 15000),
            lista_arquivos=agent_params.get('lista_arquivos'),
            retornar_lista_arquivos=agent_params.get('retornar_lista_arquivos', False),
            modo_adicao_incremental=agent_params.get('modo_adicao_incremental', False),
            usuario_executor=agent_params.get('usuario_executor'),
            job_id=agent_params.get('job_id'),
            projeto=agent_params.get('projeto')
        )
