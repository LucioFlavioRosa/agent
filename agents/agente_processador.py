import json
from typing import Optional, Dict, Any, List

from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteProcessador:
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    def main(
        self,
        tipo_analise: str,
        codigo: Dict[str, Any],
        repositorio: Optional[str] = None,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        modo_batch: bool = False,
        prompts_batch: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if modo_batch and prompts_batch:
            if not hasattr(self.llm_provider, 'executar_prompt_batch'):
                raise ValueError("Provider não suporta modo batch")
            
            resultados_batch = self.llm_provider.executar_prompt_batch(
                tipo_tarefa=tipo_analise,
                prompts_principais=prompts_batch,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=max_token_out
            )
            
            return {
                "resultado": {
                    "reposta_final": resultados_batch
                }
            }
        
        codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)

        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }