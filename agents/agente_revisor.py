import logging
from typing import Any, Dict

class AgenteRevisor:
    def __init__(self, llm_service):
        self.llm_service = llm_service

    def processar(self, agent_params: Dict[str, Any]) -> Any:
        current_batch = agent_params.get('current_batch')
        if current_batch is not None:
            batch_index = agent_params.get('batch_index', 0)
            total_batches = agent_params.get('total_batches', 1)
            logging.info(f"Processando batch {batch_index+1}/{total_batches} com {len(current_batch)} steps")
            prompt_steps = current_batch
        else:
            prompt_steps = agent_params.get('steps', [])
        prompt = self._montar_prompt(prompt_steps, agent_params)
        resposta = self.llm_service.enviar_prompt(prompt)
        return resposta

    def _montar_prompt(self, steps, agent_params):
        # Monta o prompt para a LLM usando apenas os steps recebidos
        return f"Aplique as seguintes mudanças: {steps}"
