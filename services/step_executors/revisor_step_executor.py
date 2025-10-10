from services.step_executors.base_step_executor import BaseStepExecutor
from typing import Dict, Any, Optional, List

class RevisorStepExecutor(BaseStepExecutor):
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], current_step_index: int,
                previous_step_result: Dict[str, Any], repo_reader, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        current_batch = agent_params.get('current_batch')
        batch_index = agent_params.get('batch_index')
        total_batches = agent_params.get('total_batches')
        if current_batch is not None:
            batch_steps = current_batch
            batch_num = batch_index + 1 if batch_index is not None else 1
            total = total_batches if total_batches is not None else 1
            steps_descriptions = []
            for s in batch_steps:
                desc = f"- Passo {s.get('numero') or s.get('Passo #')}: {s.get('descricao') or s.get('Descrição')} (Arquivo: {s.get('caminho') or s.get('Caminho do Arquivo')})"
                steps_descriptions.append(desc)
            instrucoes = f"Aplique as seguintes mudanças (Batch {batch_num}/{total}):\n" + '\n'.join(steps_descriptions)
            agent_params = dict(agent_params)
            agent_params['instrucoes'] = instrucoes
        return llm_provider.run_agent(
            job_id=job_id,
            job_info=job_info,
            step=step,
            current_step_index=current_step_index,
            previous_step_result=previous_step_result,
            repo_reader=repo_reader,
            agent_params=agent_params
        )
