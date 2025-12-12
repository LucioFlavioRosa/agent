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
        codigo: Optional[Dict[str, Any]] = None,
        repository_type: str = None,
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
        project_id: Optional[str] = None,
        arquivo_docx: Optional[str] = None,
        nome_projeto: Optional[str] = None,
        instrucoes_padrao: Optional[str] = None
    ) -> Dict[str, Any]:
        if instrucoes_extras is None:
            instrucoes_extras = ""
        if instrucoes_padrao is None:
            instrucoes_padrao = ""
        instrucoes_combinadas = f"{instrucoes_padrao}\n{instrucoes_extras}" if instrucoes_padrao or instrucoes_extras else ""
        print(f"[AgenteProcessador] instrucoes_combinadas: {instrucoes_combinadas[:200]}")
        if codigo is not None and codigo != {}:
            if lista_arquivos:
                print(f"[Agente Processador] Lista de arquivos recebida: {len(lista_arquivos)} arquivos totais no repositório")
                codigo_str = json.dumps({
                    'arquivos_codigo': codigo,
                    'lista_todos_arquivos': lista_arquivos
                }, indent=2, ensure_ascii=False)
            else:
                codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)
        else:
            if lista_arquivos:
                codigo_str = json.dumps({'lista_todos_arquivos': lista_arquivos}, indent=2, ensure_ascii=False)
            else:
                codigo_str = json.dumps({'sem_codigo_base': True}, indent=2, ensure_ascii=False)

        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_combinadas,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        log_custom_data(
            job_id=job_id,
            project_id=project_id,
            data_hora=datetime.now(timezone.utc).isoformat(),
            tipo_analise=tipo_analise,
            model_name=model_name,
            tokens_in=resultado_da_ia.get('tokens_entrada'),
            tokens_out=resultado_da_ia.get('tokens_saida')
        )

        return {"resultado": {"reposta_final": resultado_da_ia}}
