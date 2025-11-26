from typing import Optional, Dict, Any

class ILLMProvider:
    def executar_prompt(self, tipo_tarefa: str, prompt_principal: Optional[str], instrucoes_extras: Optional[str], usar_rag: bool = False, model_name: Optional[str] = None, max_token_out: int = 15000, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()
