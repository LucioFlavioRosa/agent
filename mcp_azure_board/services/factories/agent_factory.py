from agents.agente_revisor_board import AgenteRevisorBoard
from domain.interfaces.llm_provider_interface import ILLMProvider
from services.azure_board_service import AzureBoardService

class AgentFactory:
    _agents = {
        'revisor_board': AgenteRevisorBoard
    }

    @classmethod
    def create_agent(
        cls,
        agent_type: str,
        azure_board_service: AzureBoardService = None,
        llm_provider: ILLMProvider = None
    ):
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        if agent_type == 'revisor_board':
            if azure_board_service is None:
                raise ValueError("Para 'revisor_board', é necessário fornecer azure_board_service.")
            if llm_provider is None:
                raise ValueError("Para 'revisor_board', é necessário fornecer llm_provider.")
            return agent_class(azure_board_service=azure_board_service, llm_provider=llm_provider)
        raise ValueError(f"Tipo de agente não suportado: {agent_type}")

    @classmethod
    def register_agent(cls, agent_type: str, agent_class) -> None:
        cls._agents[agent_type] = agent_class
