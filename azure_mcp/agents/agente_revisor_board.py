import logging
from azure_mcp.tools.prompts.criacao_epicos import PROMPT_CRIACAO_EPICOS
from azure_mcp.tools.prompts.criacao_features_azure_devops import PROMPT_CRIACAO_FEATURES
from azure_mcp.tools.prompts.criacao_tarefas_azure_devops import PROMPT_CRIACAO_TAREFAS
from azure_mcp.tools.prompts.melhoria_de_tarefas import PROMPT_MELHORIA_TAREFAS
from azure_mcp.tools.prompts.melhorias_azure import PROMPT_MELHORIAS_AZURE

class AgenteRevisorBoard:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def executar(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        logging.info(f"[AgenteRevisorBoard] Executando agente revisor_board para job {job_id}")
        analysis_type = job_info['data'].get('original_analysis_type')
        prompt = self._selecionar_prompt(analysis_type)
        resposta = self.llm_provider.gerar_resposta(prompt, agent_params)
        return {
            'job_id': job_id,
            'step_index': current_step_index,
            'resposta': resposta,
            'analysis_type': analysis_type
        }

    def _selecionar_prompt(self, analysis_type):
        if analysis_type == 'criacao_epicos_azure_devops':
            return PROMPT_CRIACAO_EPICOS
        elif analysis_type == 'criacao_features_azure_devops':
            return PROMPT_CRIACAO_FEATURES
        elif analysis_type == 'criacao_tarefas_azure_devops':
            return PROMPT_CRIACAO_TAREFAS
        elif analysis_type == 'revisor_tarefas':
            return PROMPT_MELHORIA_TAREFAS
        else:
            return PROMPT_MELHORIAS_AZURE
