from typing import Optional, Dict, Type
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
import os

class LLMProviderFactory:
    _providers: Dict[str, Type[ILLMProvider]] = {
        'openai': OpenAILLMProvider,
        'claude': AnthropicClaudeProvider
    }
    
    @classmethod
    def create_provider(cls, model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
        model_lower = (model_name or "").lower()
        
        if "claude" in model_lower:
            provider_class = cls._providers.get('claude', OpenAILLMProvider)
        else:
            provider_class = cls._providers.get('openai', OpenAILLMProvider)
        
        return provider_class(rag_retriever=rag_retriever)

    @classmethod
    def register_provider(cls, key: str, provider_class: Type[ILLMProvider]) -> None:
        cls._providers[key] = provider_class

    @staticmethod
    def executar_prompt(tipo_tarefa: str, prompt_principal: str, instrucoes_extras: Optional[str] = None, usar_rag: bool = False, model_name: Optional[str] = None, max_token_out: int = 15000, **kwargs):
        if tipo_tarefa == 'aplicacao_incremental_mudanca':
            prompt_path = os.path.join(os.path.dirname(__file__), '../../tools/prompts/aplicacao_incremental_mudanca.md')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            task_description = kwargs.get('task_description', '')
            file_path = kwargs.get('file_path', '')
            current_file_content = kwargs.get('current_file_content', '')
            related_files_content = kwargs.get('related_files_content', '')
            previous_task_results = kwargs.get('previous_task_results', '')
            prompt_final = prompt_template.replace('{task_description}', task_description)
            prompt_final = prompt_final.replace('{file_path}', file_path)
            prompt_final = prompt_final.replace('{current_file_content}', current_file_content)
            prompt_final = prompt_final.replace('{related_files_content}', related_files_content)
            prompt_final = prompt_final.replace('{previous_task_results}', previous_task_results)
            provider = LLMProviderFactory.create_provider(model_name, kwargs.get('rag_retriever'))
            return provider.executar_prompt(
                tipo_tarefa=tipo_tarefa,
                prompt_principal=prompt_final,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=8000
            )
        else:
            provider = LLMProviderFactory.create_provider(model_name, kwargs.get('rag_retriever'))
            return provider.executar_prompt(
                tipo_tarefa=tipo_tarefa,
                prompt_principal=prompt_principal,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=max_token_out
            )
