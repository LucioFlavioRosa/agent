import json
from typing import Optional, Dict, Any
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteRevisor:
    """
    Orquestrador de análise de código via IA.
    Sua única responsabilidade é ler um repositório do GitHub e iniciar uma análise.
    """
    def __init__(
        self,
        repository_reader: IRepositoryReader,
        llm_provider: ILLMProvider
    ):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str
    ) -> Dict[str, str]:
        """
        Função interna para ler o código de um repositório usando a interface injetada.
        """
        try:
            print(f"Iniciando a leitura do repositório: {repositorio}, branch: {nome_branch}")
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch
            )
            return codigo_para_analise
        except Exception as e:
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

    def main(
        self,
        tipo_analise: str,
        repositorio: str,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Função principal do agente. Orquestra a obtenção do código de um repositório
        e a chamada para a IA.
        """
        codigo_para_analise = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise
        )

        if not codigo_para_analise:
            print(f"AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            return {"resultado": {"reposta_final": {}}}

        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)

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
        
