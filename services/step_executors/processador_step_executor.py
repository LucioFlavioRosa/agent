from agents.agente_processador import AgenteProcessador
from domain.interfaces.llm_provider_interface import ILLMProvider

class ProcessadorStepExecutor:
    def __init__(self, llm_provider: ILLMProvider):
        self.agent = AgenteProcessador(llm_provider)

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        tipo_analise = agent_params.get('tipo_analise')
        codigo = agent_params.get('codigo')
        repository_type = agent_params.get('repository_type')
        repositorio = agent_params.get('repositorio')
        nome_branch = agent_params.get('nome_branch')
        instrucoes_extras = agent_params.get('instrucoes_extras', "")
        usar_rag = agent_params.get('usar_rag', False)
        model_name = agent_params.get('model_name')
        max_token_out = agent_params.get('max_token_out', 15000)
        lista_arquivos = None
        retornar_lista_arquivos = agent_params.get('retornar_lista_arquivos', False)

        # Passo 12: Se a flag estiver ativa e previous_step_result tiver lista_arquivos, propague
        if retornar_lista_arquivos and previous_step_result and isinstance(previous_step_result, dict):
            if 'lista_arquivos' in previous_step_result:
                lista_arquivos = previous_step_result['lista_arquivos']

        resultado = self.agent.main(
            tipo_analise=tipo_analise,
            codigo=codigo,
            repository_type=repository_type,
            repositorio=repositorio,
            nome_branch=nome_branch,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out,
            lista_arquivos=lista_arquivos,
            retornar_lista_arquivos=retornar_lista_arquivos
        )
        return resultado