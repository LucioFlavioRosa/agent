from agents.agente_revisor import AgenteRevisor
from agents.agente_comparador import AgenteComparador

class AgentFactory:
    @staticmethod
    def create_agent(agent_type: str, repo_reader, llm_provider):
        if agent_type == "revisor":
            return AgenteRevisor(repo_reader, llm_provider)
        elif agent_type == "comparador":
            return AgenteComparador(repo_reader, llm_provider)
        else:
            raise ValueError(f"Tipo de agente não suportado: {agent_type}")

# Todas as referências e lógica de criação para AgenteProcessador e AgenteRevisorCodigo foram removidas.
