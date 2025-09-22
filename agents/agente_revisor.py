import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data

class AgenteRevisor:

    def __init__(
        self,
        repository_reader: IRepositoryReader,
        llm_provider: ILLMProvider
    ):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider
        init_logger()

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str,
        repository_type: str,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        try:
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                repository_type=repository_type,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos
            )
                
            return codigo_para_analise
            
        except Exception as e:
            print(f"[Agente Revisor] ERRO durante leitura do repositório: {e}")
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

    def _get_comparison_codes(
        self,
        repositorio: str,
        repository_type: str,
        codigo_original_branch: Optional[str],
        codigo_original_arquivos: Optional[List[str]],
        codigo_modernizado_branch: Optional[str],
        codigo_modernizado_arquivos: Optional[List[str]]
    ) -> Dict[str, Dict[str, str]]:
        comparison_data = {}
        
        if codigo_original_branch and codigo_original_arquivos:
            try:
                codigo_original = self.repository_reader.read_repository(
                    nome_repo=repositorio,
                    tipo_analise="comparacao",
                    repository_type=repository_type,
                    nome_branch=codigo_original_branch,
                    arquivos_especificos=codigo_original_arquivos
                )
                comparison_data["codigo_original"] = codigo_original
                print(f"[Agente Revisor] Código original carregado: {len(codigo_original)} arquivos")
            except Exception as e:
                print(f"[Agente Revisor] ERRO ao carregar código original: {e}")
                comparison_data["codigo_original"] = {}
        
        if codigo_modernizado_branch and codigo_modernizado_arquivos:
            try:
                codigo_modernizado = self.repository_reader.read_repository(
                    nome_repo=repositorio,
                    tipo_analise="comparacao",
                    repository_type=repository_type,
                    nome_branch=codigo_modernizado_branch,
                    arquivos_especificos=codigo_modernizado_arquivos
                )
                comparison_data["codigo_modernizado"] = codigo_modernizado
                print(f"[Agente Revisor] Código modernizado carregado: {len(codigo_modernizado)} arquivos")
            except Exception as e:
                print(f"[Agente Revisor] ERRO ao carregar código modernizado: {e}")
                comparison_data["codigo_modernizado"] = {}
        
        return comparison_data

    def _prepare_comparison_prompt(
        self,
        comparison_data: Dict[str, Dict[str, str]],
        instrucoes_comparacao_markdown: str
    ) -> str:
        prompt_parts = []
        
        if "codigo_original" in comparison_data and comparison_data["codigo_original"]:
            prompt_parts.append("=== CÓDIGO ORIGINAL ===")
            prompt_parts.append(json.dumps(comparison_data["codigo_original"], indent=2, ensure_ascii=False))
            prompt_parts.append("")
        
        if "codigo_modernizado" in comparison_data and comparison_data["codigo_modernizado"]:
            prompt_parts.append("=== CÓDIGO MODERNIZADO ===")
            prompt_parts.append(json.dumps(comparison_data["codigo_modernizado"], indent=2, ensure_ascii=False))
            prompt_parts.append("")
        
        if instrucoes_comparacao_markdown:
            prompt_parts.append("=== INSTRUÇÕES DE COMPARAÇÃO ===")
            prompt_parts.append(instrucoes_comparacao_markdown)
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)

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
        arquivos_especificos: Optional[List[str]] = None,
        job_id: Optional[str] = None,
        projeto: Optional[str] = None,
        status_update: Optional[str] = None,
        codigo_original_branch: Optional[str] = None,
        codigo_original_arquivos: Optional[List[str]] = None,
        codigo_modernizado_branch: Optional[str] = None,
        codigo_modernizado_arquivos: Optional[List[str]] = None,
        instrucoes_comparacao_markdown: Optional[str] = None
    ) -> Dict[str, Any]:

        log_custom_data(
            job_id=job_id,
            projeto=projeto,
            data_hora=datetime.now(timezone.utc).isoformat(),
            status="INICIADO",
            tipo_repositorio=repository_type,
            nome_repositorio=repositorio,
            tipo_analise=tipo_analise,
            model_name=model_name
        )

        is_comparison_mode = (
            codigo_original_branch or codigo_original_arquivos or 
            codigo_modernizado_branch or codigo_modernizado_arquivos or 
            instrucoes_comparacao_markdown
        )

        if is_comparison_mode:
            print(f"[Agente Revisor] Modo comparação ativado para job {job_id}")
            
            comparison_data = self._get_comparison_codes(
                repositorio=repositorio,
                repository_type=repository_type,
                codigo_original_branch=codigo_original_branch,
                codigo_original_arquivos=codigo_original_arquivos,
                codigo_modernizado_branch=codigo_modernizado_branch,
                codigo_modernizado_arquivos=codigo_modernizado_arquivos
            )
            
            if not comparison_data:
                print(f"[Agente Revisor] AVISO: Nenhum código de comparação foi carregado")
                return {"resultado": {"reposta_final": {}}}
            
            prompt_principal = self._prepare_comparison_prompt(
                comparison_data, instrucoes_comparacao_markdown or ""
            )
            
            instrucoes_extras_completas = f"{instrucoes_extras}\n\nEsta é uma análise de comparação entre código original e modernizado."
        else:
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
                
                log_custom_data(
                    job_id=job_id,
                    projeto=projeto,
                    status="ERRO_SEM_CODIGO",
                    repositorio=repositorio,
                    tipo_analise=tipo_analise,
                    data_hora=datetime.now(timezone.utc).isoformat()
                )
                
                return {"resultado": {"reposta_final": {}}}

            prompt_principal = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)
            instrucoes_extras_completas = instrucoes_extras

        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=prompt_principal,
            instrucoes_extras=instrucoes_extras_completas,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out,
        )

        log_custom_data(
            job_id=job_id,
            projeto=projeto,
            data_hora=datetime.now(timezone.utc).isoformat(),
            tokens_in=resultado_da_ia['tokens_entrada'],
            tokens_out=resultado_da_ia['tokens_saida'],
            status='FINALIZADO',
            tipo_repositorio=repository_type,
            nome_repositorio=repositorio,
            tipo_analise=tipo_analise,
            model_name=model_name,
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }