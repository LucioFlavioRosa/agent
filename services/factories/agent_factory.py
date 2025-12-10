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
        repository_reader: ReaderGeral = None,
        llm_provider: ILLMProvider = None,
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
        if agent_type in ["revisor", "comparador"]:
            return agent_class(repository_reader=repository_reader, llm_provider=llm_provider)
        elif agent_type == "processador":
            return agent_class(llm_provider=llm_provider)
        return agent_class()
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type) -> None:
        cls._agents[agent_type] = agent_class
