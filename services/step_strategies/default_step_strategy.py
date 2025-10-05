from typing import Dict, Any

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def should_finalize_workflow(self, job_info: Dict[str, Any], step_index: int) -> bool:
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        if step_index == 0 and gerar_relatorio_apenas:
            return True
        return False

    def should_pause_for_approval(self, step: Dict[str, Any], job_info: Dict[str, Any]) -> bool:
        requires_approval = step.get('requires_approval', False)
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        if requires_approval and not gerar_relatorio_apenas:
            return True
        return False

    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], current_step_index: int, previous_step_result: Dict[str, Any], repo_reader, llm_provider, agent_params) -> Dict[str, Any]:
        agent_type = step.get('agent', 'default')
        if hasattr(llm_provider, 'executar_agente'):
            return llm_provider.executar_agente(agent_type, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params)
        else:
            raise NotImplementedError(f"Agente {agent_type} não implementado no provider.")
