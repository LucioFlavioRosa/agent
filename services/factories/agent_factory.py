from services.agent_validator_service import AgentValidatorService

class AgentFactory:
    @staticmethod
    def create_agent(agent_type, repo_reader, llm_provider):
        # Validação: agentes de análise de código sempre exigem repo_reader
        if AgentValidatorService.validate_agent_requires_repository(agent_type):
            if repo_reader is None:
                raise ValueError(f"O agente '{agent_type}' requer um repositório válido (repo_reader não pode ser None).")
        # Instanciação do agente (exemplo, adapte conforme implementação real)
        if agent_type == "review":
            from agents.agente_revisor import AgenteRevisor
            return AgenteRevisor(repo_reader, llm_provider)
        elif agent_type == "improve":
            from agents.agente_processador import AgenteProcessador
            return AgenteProcessador(repo_reader, llm_provider)
        elif agent_type == "revisor":
            from agents.agente_revisor_codigo import AgenteRevisorCodigo
            return AgenteRevisorCodigo(repo_reader, llm_provider)
        elif agent_type == "comparador":
            from agents.agente_comparador import AgenteComparador
            return AgenteComparador(repo_reader, llm_provider)
        else:
            raise ValueError(f"Tipo de agente '{agent_type}' não suportado ou não requer repositório.")
