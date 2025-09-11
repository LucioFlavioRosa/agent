from typing import Dict, Type, Any
from agents.agente_revisor import AgenteRevisor
from agents.agente_processador import AgenteProcessador
from agents.agente_implementador import AgenteImplementador
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.readers.reader_geral import ReaderGeral

class AgentFactory:
    _agents: Dict[str, Type] = {
        'revisor': AgenteRevisor,
        'processador': AgenteProcessador,
        'implementador': AgenteImplementador
    }
    
    @classmethod
    def create_agent(cls, agent_type: str, repository_reader: ReaderGeral = None, 
                    llm_provider: ILLMProvider = None):
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        
        if agent_type == "revisor":
            return agent_class(repository_reader=repository_reader, llm_provider=llm_provider)
        elif agent_type == "processador":
            return agent_class(llm_provider=llm_provider)
        elif agent_type == "implementador":
            return agent_class(llm_provider=llm_provider)
        
        return agent_class()
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type) -> None:
        cls._agents[agent_type] = agent_class