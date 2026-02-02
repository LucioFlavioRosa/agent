import json
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.factories.llm_provider_factory import LLMProviderFactory
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider_explicit
from models import JobFields
import traceback

# Nenhuma referência direta ou indireta ao AgenteProcessador ou ao agents/agente_processador.py foi encontrada neste arquivo.
# Imports e lógica relacionados ao agente processador não existem neste contexto.
# O arquivo está pronto para futura remoção de dependências caso sejam identificadas em outros arquivos/factories.

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 secret_manager: Optional[Any] = None, cache_service=None, dependency_container=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service)
        self.secret_manager = secret_manager
        self.dependency_container = dependency_container

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any], current_step_index: int) -> bool:
        print(f"[{job_id}] [DEBUG] Entrando em _save_generated_report para step {current_step_index}.")
        report_text = self.report_handler.extract_report_text(step_result)
        print(f"[{job_id}] [DEBUG] extract_report_text retornou: {str(report_text)[:200]}...")
        if not report_text or len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio no step {current_step_index}.")
            return False
        job_info['data']['analysis_report'] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] [DEBUG] save_report_to_blob retornou url: {url}")
        if not url:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
        job_info['data']['report_blob_url'] = url
        self.job_handler.update_job(job_id, job_info)
        try:
            if job_info['data'].get('report_blob_url'):
                self.report_handler.blob_storage.update_job_tracker(job_info['data']['report_blob_url'], job_id)
        except Exception as e:
            print(f"[WorkflowOrchestrator] Warning: Failed to update job tracker after saving report: {e}")
        print(f"[{job_id}] [DEBUG] _save_generated_report finalizado com sucesso para step {current_step_index}.")
        return True

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        repo_name_modernizado = job_info['data'].get('repo_name_modernizado')
        analysis_type = job_info['data'].get('original_analysis_type', '')
        if not repo_name_modernizado:
            raise ValueError("O campo 'repo_name_modernizado' é obrigatório em job_info['data'] para execução do workflow.")
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            projeto = job_info['data'].get('projeto')
            repository_type = job_info['data'].get('repository_type')
            repo_name = job_info['data'].get('repo_name')
            branch_name = job_info['data'].get('branch_name_modernizado')
            analysis_name = job_info['data'].get('analysis_name')
            # Sempre lê do repositório antes de rodar análise
            repository_provider = get_repository_provider_explicit(repository_type)
            cache_service = self.cache_service or (self.dependency_container.get_redis_cache_service() if self.dependency_container else None)
            repo_reader = ReaderGeral(repository_provider=repository_provider, cache_service=cache_service)
            steps = workflow.get('steps', [])
            if not steps:
                raise ValueError("Workflow não possui steps definidos.")
            step = steps[0]
            print(f"[{job_id}] Executando step 0 (análise)")
            self.job_handler.update_job_status(job_id, step.get('status_update', 'processing'))
            previous_step_result = None
            step_result = self._execute_step_with_strategy(
                job_id, job_info, step, 0, previous_step_result, repo_reader, 0, start_from_step
            )
            print(f"[{job_id}] [DEBUG] Resultado do agente: {str(step_result)[:300]}...")
            report_saved = self._save_generated_report(job_id, job_info, step_result, 0)
            print(f"[{job_id}] [DEBUG] _save_generated_report retornou {report_saved}")
            self.job_handler.update_job_status(job_id, 'completed')
        except Exception as e:
            error_message = str(e)
            print(f"[{job_id}] ERRO FATAL NO WORKFLOW: {error_message}")
            traceback.print_exc()
            try:
                if job_info and 'data' in job_info:
                    job_info['data']['error_details'] = error_message
                    self.job_handler.update_job(job_id, job_info)
            except Exception as update_err:
                print(f"[{job_id}] ERRO CRÍTICO: Falha ao salvar detalhes do erro no job: {update_err}")
            self.job_handler.update_job_status(job_id, 'failed')

    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                    current_step_index: int, previous_step_result: Dict[str, Any], 
                                    repo_reader: ReaderGeral, step_iteration: int, 
                                    start_from_step: int, batch_steps: Optional[list] = None, 
                                    agent_params_override: Optional[dict] = None) -> Dict[str, Any]:
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy() if step.get('params') else {}
        agent_type = step.get('agent_type', step.get('agent'))
        analysis_type = job_info['data'].get('original_analysis_type')
        agent_params['instrucoes_extras'] = job_info['data'].get('instrucoes_extras', '')
        repo_name = job_info['data'].get('repo_name_modernizado')
        branch_name = job_info['data'].get('branch_name_modernizado')
        if branch_name:
            agent_params['nome_branch'] = branch_name
        agent_params['repositorio'] = repo_name
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa,
            'repository_type': job_info['data']['repository_type'],
            'retornar_lista_arquivos': job_info.get('data', {}).get('retornar_lista_arquivos', False),
            'usuario_executor': job_info.get('data', {}).get('usuario_executor')
        })
        agent_params['job_id'] = job_id
        if agent_params_override:
            agent_params.update(agent_params_override)
        strategy = step.get('strategy')
        if strategy:
            strategy_instance = strategy(self.job_handler)
            result = strategy_instance.execute_step(
                job_id, job_info, step, current_step_index, 
                previous_step_result, repo_reader, llm_provider, agent_params
            )
        else:
            # fallback: agente simples
            # Nenhuma referência ao AgenteProcessador ou agente_processador.py
            result = llm_provider.run_agent(
                agent_type, agent_params, repo_reader=repo_reader
            )
        print(f"[{job_id}] [DEBUG] strategy.execute_step retornou resultado para step {current_step_index}: {str(result)[:300]}...")
        return result
