import json
from typing import Optional, Dict, Any, List
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteRevisor:
    
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
        tipo_analise: str,
        repository_type: str,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        try:
            print(f"[Agente Revisor] Parâmetros de entrada:")
            print(f"[Agente Revisor] - repositorio: {repositorio}")
            print(f"[Agente Revisor] - nome_branch: {nome_branch}")
            print(f"[Agente Revisor] - tipo_analise: {tipo_analise}")
            print(f"[Agente Revisor] - repository_type: {repository_type}")
            print(f"[Agente Revisor] - arquivos_especificos: {arquivos_especificos}")
            
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"[Agente Revisor] Iniciando a leitura filtrada do repositório: {repositorio}, branch: {nome_branch}, tipo: {repository_type}")
                print(f"[Agente Revisor] Arquivos específicos solicitados: {len(arquivos_especificos)} arquivos")
            else:
                print(f"[Agente Revisor] Iniciando a leitura completa do repositório: {repositorio}, branch: {nome_branch}, tipo: {repository_type}")
            
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos
            )
            
            print(f"[Agente Revisor] Resultado da leitura: {type(codigo_para_analise)} com {len(codigo_para_analise) if codigo_para_analise else 0} itens")
            
            if not codigo_para_analise:
                print(f"[Agente Revisor] AVISO CRÍTICO: codigo_para_analise está vazio")
                print(f"[Agente Revisor] Tipo do objeto retornado: {type(codigo_para_analise)}")
                print(f"[Agente Revisor] Conteúdo do objeto: {codigo_para_analise}")
            else:
                print(f"[Agente Revisor] Arquivos obtidos: {list(codigo_para_analise.keys())[:3]}{'...' if len(codigo_para_analise) > 3 else ''}")
            
            return codigo_para_analise
            
        except Exception as e:
            print(f"[Agente Revisor] ERRO durante leitura do repositório: {e}")
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

    def main(
        self,
        tipo_analise: str,
        repositorio: str,
        repository_type: str,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        print(f"[Agente Revisor] Iniciando análise - repositório: {repositorio} (tipo: {repository_type})")
        
        codigo_para_analise = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise,
            repository_type=repository_type,
            arquivos_especificos=arquivos_especificos
        )

        if not codigo_para_analise:
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"[Agente Revisor] AVISO: Nenhum dos arquivos específicos foi encontrado no repositório para a análise '{tipo_analise}'.")
            else:
                print(f"[Agente Revisor] AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            
            print(f"[Agente Revisor] Retornando resposta vazia devido à ausência de código")
            return {"resultado": {"reposta_final": {}}}

        print(f"[Agente Revisor] Preparando código para envio à IA ({len(codigo_para_analise)} arquivos)")
        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)
        print(f"[Agente Revisor] Tamanho do JSON de código: {len(codigo_str)} caracteres")

        print(f"[Agente Revisor] Enviando para LLM Provider (modelo: {model_name})")
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        print(f"[Agente Revisor] Resposta recebida da IA: {type(resultado_da_ia)}")
        if resultado_da_ia:
            print(f"[Agente Revisor] Conteúdo da resposta (primeiros 200 chars): {str(resultado_da_ia)[:200]}...")
        else:
            print(f"[Agente Revisor] AVISO CRÍTICO: IA retornou resposta vazia ou None")

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }