import json
from typing import Dict, Any
from domain.interfaces.agent_interface import IAgent
from services.agents.revisor_agent import RevisorAgent
from services.agents.processador_agent import ProcessadorAgent
from services.factories.llm_provider_factory import LLMProviderFactory

class AgentExecutor:
    def __init__(self, rag_retriever):
        self.rag_retriever = rag_retriever
    
    def create_agent(self, agent_type: str, repo_reader, job_info: Dict[str, Any], step: Dict[str, Any]) -> IAgent:
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        
        if agent_type == "revisor":
            return RevisorAgent(repo_reader, llm_provider)
        elif agent_type == "processador":
            return ProcessadorAgent(repo_reader, llm_provider)
        else:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
    
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                    current_step_index: int, previous_step_result: Dict[str, Any], 
                    repo_reader) -> Dict[str, Any]:
        
        agent_type = step.get("agent_type")
        agent = self.create_agent(agent_type, repo_reader, job_info, step)
        
        agent_response = agent.execute(
            job_id=job_id,
            job_info=job_info,
            step=step,
            current_step_index=current_step_index,
            previous_step_result=previous_step_result
        )
        
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("", "").replace("", "").strip()
        
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
        
        return json.loads(cleaned_string)