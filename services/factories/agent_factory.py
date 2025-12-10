from typing import Dict, Type, Any
from agents.agente_processador import AgenteProcessador
from domain.interfaces.llm_provider_interface import ILLMProvider

class AgentFactory:
    _agents: Dict[str, Type] = {
        'processador': AgenteProcessador
    }
    
    @classmethod
    def create_agent(
        cls,
        agent_type: str,
        llm_provider: ILLMProvider = None,
    ):
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")

        elif agent_type == "processador":
            return agent_class(llm_provider=llm_provider)
        return agent_class()
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type) -> None:
        cls._agents[agent_type] = agent_class
