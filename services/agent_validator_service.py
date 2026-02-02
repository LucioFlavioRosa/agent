class AgentValidatorService:
    """
    Serviço para validar se um agente requer um repositório para execução.
    """
    _agents_requiring_repository = {'review', 'improve', 'revisor', 'comparador'}

    @classmethod
    def validate_agent_requires_repository(cls, agent_type: str) -> bool:
        """
        Retorna True se o agente requer um repositório, False caso contrário.
        """
        return agent_type in cls._agents_requiring_repository
