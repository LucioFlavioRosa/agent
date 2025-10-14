import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data

class AgenteRevisor:
    def __init__(self, repository_reader: IRepositoryReader, llm_provider: ILLMProvider):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider
        init_logger()
    def _get_code(self, repositorio: str, nome_branch: Optional[str], tipo_analise: str, repository_type: str, arquivos_especificos: Optional[List[str]] = None, retornar_lista_arquivos: bool = False) -> Dict[str, Any]:
        try:
            if repository_type == 'azure':
                parts = repositorio.split('/')
                if len(parts) != 3:
                    raise ValueError(f"[agente_revisor] repositorio para Azure deve estar no formato organization/project/repository. Recebido: {repositorio}")
            print(f"[DEBUG][agente_revisor] Chamando read_repository com repositorio={repositorio}, tipo={repository_type}")
            resultado = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                repository_type=repository_type,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos,
                retornar_lista_arquivos=retornar_lista_arquivos
            )
            if retornar_lista_arquivos and isinstance(resultado, dict) and 'codigo' in resultado:
                return {
                    'codigo': resultado['codigo'],
                    'lista_arquivos': resultado.get('lista_arquivos', [])
                }
            else:
                return {'codigo': resultado, 'lista_arquivos': []}
        except Exception as e:
            print(f"[Agente Revisor] ERRO durante leitura do repositório: {e}")
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e
    def main(self, tipo_analise: str, repositorio: str, repository_type: str, nome_branch: Optional[str] = None, instrucoes_extras: str = "", usar_rag: bool = False, model_name: Optional[str] = None, max_token_out: int = 15000, arquivos_especificos: Optional[List[str]] = None, job_id: Optional[str] = None, projeto: Optional[str] = None, status_update: Optional[str] = None, retornar_lista_arquivos: bool = False, modo_adicao_incremental: bool = False, usuario_executor: Optional[str] = None, current_batch: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:
        resultado_leitura = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise,
            repository_type=repository_type,
            arquivos_especificos=arquivos_especificos,
            retornar_lista_arquivos=retornar_lista_arquivos
        )
        codigo_para_analise = resultado_leitura.get('codigo', {})
        lista_arquivos = resultado_leitura.get('lista_arquivos', [])
        if not codigo_para_analise:
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"[Agente Revisor] AVISO: Nenhum dos arquivos específicos foi encontrado no repositório para a análise '{tipo_analise}'.")
            else:
                print(f"[Agente Revisor] AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            print(f"[Agente Revisor] Retornando resposta vazia devido à ausência de código")
            return {"resultado": {"reposta_final": {}}}
        if lista_arquivos:
            print(f"[Agente Revisor] Lista de arquivos recebida: {len(lista_arquivos)} arquivos totais no repositório")
            codigo_str = json.dumps({
                'arquivos_codigo': codigo_para_analise,
                'lista_todos_arquivos': lista_arquivos
            }, indent=2, ensure_ascii=False)
        else:
            codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)
        if current_batch is not None and isinstance(current_batch, list) and len(current_batch) > 0:
            batch_instrucao = "ATENÇÃO: Processar APENAS os passos listados abaixo. Ignorar todos os outros passos do relatório original.\n"
            batch_instrucao += json.dumps(current_batch, indent=2, ensure_ascii=False)
            if instrucoes_extras:
                instrucoes_extras += "\n\n" + batch_instrucao
            else:
                instrucoes_extras = batch_instrucao
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
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
            modo_adicao_incremental=modo_adicao_incremental,
            usuario_executor=usuario_executor
        )
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }
