from agents.agente_revisor_board import AgenteRevisorBoard
from typing import Dict, Type, Any

class AgentFactory:
    _agents: Dict[str, Type] = {
        'revisor_board': AgenteRevisorBoard
    }
    
    @classmethod
    def create_agent(
        cls,
        agent_type: str,
        azure_board_service: Any = None,
        llm_provider: Any = None
    ):
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        return agent_class(azure_board_service=azure_board_service, llm_provider=llm_provider)
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type) -> None:
        cls._agents[agent_type] = agent_class
