import os
from services.llm_provider import LLMProvider

class LLMProviderFactory:
    @staticmethod
    def create_provider(model_name=None, rag_retriever=None):
        return LLMProvider(model_name=model_name, rag_retriever=rag_retriever)

    @staticmethod
    def executar_prompt(tipo_tarefa, prompt_principal, instrucoes_extras=None, usar_rag=False, model_name=None, max_token_out=15000, **kwargs):
        if tipo_tarefa == "aplicacao_incremental_mudanca":
            prompt_path = os.path.join(os.path.dirname(__file__), "../../tools/prompts/aplicacao_incremental_mudanca.md")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            task_description = kwargs.get("task_description", "")
            file_path = kwargs.get("file_path", "")
            current_file_content = kwargs.get("current_file_content", "")
            related_files_content = kwargs.get("related_files_content", "")
            previous_task_results = kwargs.get("previous_task_results", "")
            prompt = prompt_template.replace("{task_description}", task_description)
            prompt = prompt.replace("{file_path}", file_path)
            prompt = prompt.replace("{current_file_content}", current_file_content)
            prompt = prompt.replace("{related_files_content}", related_files_content)
            prompt = prompt.replace("{previous_task_results}", previous_task_results)
            provider = LLMProviderFactory.create_provider(model_name=model_name)
            return provider.executar_prompt(
                tipo_tarefa=tipo_tarefa,
                prompt_principal=prompt,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=8000
            )
        else:
            provider = LLMProviderFactory.create_provider(model_name=model_name)
            return provider.executar_prompt(
                tipo_tarefa=tipo_tarefa,
                prompt_principal=prompt_principal,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=max_token_out
            )
