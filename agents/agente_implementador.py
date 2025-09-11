import json
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteImplementador:
    
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    def main(
        self,
        plano_de_acao: Dict[str, Any],
        base_de_codigo: Dict[str, Any],
        observacoes_do_usuario: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        
        prompt_dados = {
            "plano_de_acao": plano_de_acao,
            "base_de_codigo": base_de_codigo,
            "observacoes_do_usuario": observacoes_do_usuario
        }
        
        prompt_principal = json.dumps(prompt_dados, indent=2, ensure_ascii=False)
        
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa="implementacao",
            prompt_principal=prompt_principal,
            instrucoes_extras=observacoes_do_usuario,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }