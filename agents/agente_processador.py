import json
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteProcessador:
    """
    Um agente simples focado em processar dados estruturados (JSON)
    que são passados de etapas anteriores em um workflow.
    """
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    def main(
        self,
        tipo_analise: str,
        # O input principal agora é o 'codigo', que esperamos ser um dicionário
        codigo: Dict[str, Any],
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Função principal do agente. Serializa o JSON de entrada e chama a IA.
        """
        codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)

        resultado_da_ia = self.llm_provider.executar_analise_llm(
            tipo_analise=tipo_analise,
            codigo=codigo_str,
            analise_extra=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }
