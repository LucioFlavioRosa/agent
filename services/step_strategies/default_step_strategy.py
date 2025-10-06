from typing import Dict, Any

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler
        self.current_job_id = None

    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], current_step_index: int,
                     previous_step_result: Dict[str, Any], repo_reader, llm_provider, agent_params) -> Dict[str, Any]:
        self.current_job_id = job_id
        # ... lógica do step executor ...
        # Placeholder para execução real
        return {"resultado": "step executado"}

    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        gerar_relatorio_apenas = self.job_handler.get_job_data_field(self.current_job_id, 'gerar_relatorio_apenas', False)
        result = not gerar_relatorio_apenas and step.get('requires_approval', False)
        print(f"[should_pause_for_approval] step_index=?, gerar_relatorio_apenas={gerar_relatorio_apenas}, requires_approval={step.get('requires_approval', False)}, result={result}")
        return result

    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        return gerar_relatorio_apenas and current_step_index == 0
