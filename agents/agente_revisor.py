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

    def _validate_common_params(self, params: Dict[str, Any]) -> None:
        required_keys = [
            'repository_type',
            'repo_name',
            'branch_name',
            'analysis_type',
            'projeto',
            'analysis_name',
            'gerar_relatorio_apenas',
            'retornar_lista_arquivos',
            'usuario_executor'
        ]
        missing = [key for key in required_keys if key not in params or params[key] is None]
        if missing:
            raise ValueError(f"Parâmetros obrigatórios ausentes: {', '.join(missing)}")

    def _get_code(
        self,
        repo_name: str,
        branch_name: Optional[str],
        analysis_type: str,
        repository_type: str,
        arquivos_especificos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {
            'repository_type': repository_type,
            'repo_name': repo_name,
            'branch_name': branch_name,
            'analysis_type': analysis_type,
            'projeto': None,
            'analysis_name': None,
            'gerar_relatorio_apenas': None,
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'usuario_executor': user_email
        }
        self._validate_common_params(params)
        try:
            resultado = self.repository_reader.read_repository(
                nome_repo=repo_name,
                tipo_analise=analysis_type,
                repository_type=repository_type,
                nome_branch=branch_name,
                arquivos_especificos=arquivos_especificos,
                retornar_lista_arquivos=retornar_lista_arquivos,
                user_email=user_email
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

    def main(
        self,
        analysis_type: str,
        repo_name: str,
        repository_type: str,
        branch_name: Optional[str] = None,
        projeto: Optional[str] = None,
        analysis_name: Optional[str] = None,
        gerar_relatorio_apenas: bool = False,
        retornar_lista_arquivos: bool = False,
        usuario_executor: Optional[str] = None,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        arquivos_especificos: Optional[List[str]] = None,
        job_id: Optional[str] = None,
        status_update: Optional[str] = None,
        current_batch: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = {
            'repository_type': repository_type,
            'repo_name': repo_name,
            'branch_name': branch_name,
            'analysis_type': analysis_type,
            'projeto': projeto,
            'analysis_name': analysis_name,
            'gerar_relatorio_apenas': gerar_relatorio_apenas,
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'usuario_executor': usuario_executor
        }
        self._validate_common_params(params)
        user_email = usuario_executor
        resultado_leitura = self._get_code(
            repo_name=repo_name,
            branch_name=branch_name,
            analysis_type=analysis_type,
            repository_type=repository_type,
            arquivos_especificos=arquivos_especificos,
            retornar_lista_arquivos=retornar_lista_arquivos,
            user_email=user_email
        )
        codigo_para_analise = resultado_leitura.get('codigo', {})
        lista_arquivos = resultado_leitura.get('lista_arquivos', [])
        if not codigo_para_analise:
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"[Agente Revisor] AVISO: Nenhum dos arquivos específicos foi encontrado no repositório para a análise '{analysis_type}'.")
            else:
                print(f"[Agente Revisor] AVISO: Nenhum código encontrado no repositório para a análise '{analysis_type}'.")
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
        # Passo 5: garantir que analysis_type seja utilizado para carregar o prompt correto
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=analysis_type,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
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
            nome_repositorio=repo_name,
            tipo_analise=analysis_type,
            model_name=model_name,
            usuario_executor=usuario_executor
        )
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }
