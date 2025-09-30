from agents.agente_revisor import AgenteRevisor
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider

class RevisorStepExecutor:
    def __init__(self, repository_reader: IRepositoryReader, llm_provider: ILLMProvider):
        self.agent = AgenteRevisor(repository_reader, llm_provider)

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        tipo_analise = agent_params.get('tipo_analise')
        repositorio = agent_params.get('repositorio')
        repository_type = agent_params.get('repository_type')
        nome_branch = agent_params.get('nome_branch')
        instrucoes_extras = agent_params.get('instrucoes_extras', "")
        usar_rag = agent_params.get('usar_rag', False)
        model_name = agent_params.get('model_name')
        max_token_out = agent_params.get('max_token_out', 15000)
        arquivos_especificos = agent_params.get('arquivos_especificos')
        projeto = agent_params.get('projeto')
        status_update = agent_params.get('status_update')
        retornar_lista_arquivos = agent_params.get('retornar_lista_arquivos', False)

        resultado = self.agent.main(
            tipo_analise=tipo_analise,
            repositorio=repositorio,
            repository_type=repository_type,
            nome_branch=nome_branch,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out,
            arquivos_especificos=arquivos_especificos,
            job_id=job_id,
            projeto=projeto,
            status_update=status_update,
            retornar_lista_arquivos=retornar_lista_arquivos
        )
        return resultado