import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data

class AgenteProcessador:
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    def main(
        self,
        tipo_analise: str,
        repository_type: str,
        repositorio: Optional[str] = None,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        lista_arquivos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False,
        modo_adicao_incremental: bool = False,
        usuario_executor: Optional[str] = None,
        job_id: Optional[str] = None,
        projeto: Optional[str] = None,
        workflow_mode: str = "code_generation",
        codigo: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if workflow_mode == "code_generation":
            if codigo is None:
                raise TypeError("O parâmetro 'codigo' é obrigatório para workflow_mode='code_generation'.")
        if lista_arquivos:
            print(f"[Agente Processador] Lista de arquivos recebida: {len(lista_arquivos)} arquivos totais no repositório")
            codigo_str = json.dumps({
                'arquivos_codigo': codigo,
                'lista_todos_arquivos': lista_arquivos
            }, indent=2, ensure_ascii=False)
        else:
            codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False) if codigo is not None else ""
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )
        log_custom_data(
            job_id=job_id,
            projeto=projeto,
            data_hora=datetime.now(timezone.utc).isoformat(),
            tokens_in=resultado_da_ia['tokens_entrada'],
            tokens_out=resultado_da_ia['tokens_saida'],
            tipo_repositorio=repository_type,
            nome_repositorio=repositorio if repositorio is not None else None,
            tipo_analise=tipo_analise,
            model_name=model_name,
            modo_adicao_incremental=modo_adicao_incremental,
            usuario_executor=usuario_executor
        )
        return {"resultado": {"reposta_final": resultado_da_ia}}
