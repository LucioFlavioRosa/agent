from services.factories.llm_provider_factory import LLMProviderFactory
from services.factories.agent_factory import AgentFactory

class LLMOrchestrator:
    def __init__(self, rag_retriever=None):
        self.rag_retriever = rag_retriever

    def execute_analysis(self, llm_request_params):
        model_name = llm_request_params.get('model_name')
        agent_type = llm_request_params.get('agent_type', 'processador')
        provider = llm_request_params.get('provider')
        llm_provider = LLMProviderFactory.create_provider(
            model_name, 
            self.rag_retriever, 
            provider_hint=provider
        )
        job_id = llm_request_params.get('job_id')
        agente = AgentFactory.create_agent(agent_type, llm_provider=llm_provider)
        resultado = agente.main(
            tipo_analise=llm_request_params.get('analysis_type'),
            project_id=llm_request_params.get('project_id'),
            instrucoes_extras=llm_request_params.get('instrucoes_extras'),
            arquivo_docx=llm_request_params.get('arquivo_docx'),
            nome_projeto=llm_request_params.get('nome_projeto'),
            usuario_executor=llm_request_params.get('usuario_executor'),
            model_name=model_name,
            instrucoes_padrao=llm_request_params.get('instrucoes_padrao'),
            job_id=job_id
        )
        return resultado
