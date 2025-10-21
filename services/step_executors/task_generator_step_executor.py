from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.llm_provider_factory import LLMProviderFactory
from tools.prompts.criacao_tarefas import TASKS_PROMPT_PATH

class TaskGeneratorStepExecutor(BaseStepExecutor):
    def __init__(self, llm_provider_factory=None):
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        epic_markdown = previous_step_result.get('analysis_report') or job_info['data'].get('analysis_report')
        observacoes_usuario = agent_params.get('instrucoes_extras') or ""
        prompt_path = TASKS_PROMPT_PATH if 'TASKS_PROMPT_PATH' in globals() else "tools/prompts/criacao_tarefas.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        llm_provider = self.llm_provider_factory.create_provider(agent_params.get('model_name'), None)
        input_data = {
            "epico_aprovado": epic_markdown,
            "observacoes_usuario": observacoes_usuario
        }
        prompt = prompt_template
        prompt += f"\n\nÉpico Aprovado:\n{epic_markdown}\n"
        if observacoes_usuario:
            prompt += f"\nObservações do Usuário:\n{observacoes_usuario}\n"
        response = llm_provider.generate(
            prompt,
            input_data=input_data,
            temperature=0.2,
            max_tokens=2048
        )
        try:
            result_json = response if isinstance(response, dict) else None
            if not result_json:
                import json
                result_json = json.loads(response)
        except Exception:
            result_json = {"erro": "Falha ao processar resposta do LLM"}
        return {
            "job_id": job_id,
            "step_type": "generate_tasks",
            "tasks_json": result_json,
            "step_index": current_step_index
        }
