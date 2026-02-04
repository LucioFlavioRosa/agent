import json
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.factories.llm_provider_factory import create_provider
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider_explicit
from schemas import JobFields
import traceback
from services.step_strategies.default_step_strategy import DefaultStepStrategy
from tools.prompt_utils import carregar_prompt
from tools.workflow_utils import resolver_tipo_analise_do_workflow

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 secret_manager: Optional[Any] = None, cache_service=None, dependency_container=None,
                 group_resolver=None):
        self.workflow_registry = workflow_registry
        self.job_handler = job_handler or JobHandler(job_manager)
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service, group_resolver=group_resolver)
        self.secret_manager = secret_manager
        self.dependency_container = dependency_container
        self.group_resolver = group_resolver

    def _extract_job_data(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        data = job_info.get('data', {})
        return {
            'projeto': data.get('projeto'),
            'repository_type': data.get('repository_type'),
            'repo_name': data.get('repo_name'),
            'branch_name': data.get('branch_name'),
            'analysis_name': data.get('analysis_name'),
            'original_analysis_type': data.get('original_analysis_type'),
            'model_name': data.get('model_name'),
            'instrucoes_extras': data.get('instrucoes_extras'),
            'retornar_lista_arquivos': data.get('retornar_lista_arquivos', False),
            'usuario_executor': data.get('usuario_executor'),
            'arquivos_especificos': data.get('arquivos_especificos')
        }

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
        job_data = self._extract_job_data(job_info)
        repo_name = job_data.get('repo_name')
        analysis_type = job_data.get('original_analysis_type', '')
        if not repo_name:
            raise ValueError("O campo 'repo_name' é obrigatório em job_info['data'] para execução do workflow.")
        workflow = self.workflow_registry.get(job_data['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            projeto = job_data.get('projeto')
            repository_type = job_data.get('repository_type')
            repo_name = job_data.get('repo_name')
            branch_name = job_data.get('branch_name')
            analysis_name = job_data.get('analysis_name')
            usuario_executor = job_data.get('usuario_executor')
            # 1. Buscar relatório existente no Blob Storage
            report_text = self.report_handler.read_existing_report_from_blob(job_id, job_info, 0)
            if report_text and len(str(report_text).strip()) > 0:
                print(f"[{job_id}] Relatório encontrado no Blob Storage. Retornando relatório existente.")
                job_info['data']['analysis_report'] = report_text
                job_info['data']['report_blob_url'] = None  # Não sobrescrever url se não houver upload novo
                self.job_handler.update_job(job_id, job_info)
                self.job_handler.update_job_status(job_id, 'completed')
                return
            # 2. Carregar prompt do arquivo correto
            # --- INÍCIO DA MODIFICAÇÃO: usa resolver_tipo_analise_do_workflow ---
            tipo_tarefa = resolver_tipo_analise_do_workflow(job_data.get('original_analysis_type'))
            try:
                prompt_principal = carregar_prompt(tipo_tarefa)
            except Exception as e:
                raise ValueError(f"[{job_id}] ERRO ao carregar prompt para tipo_tarefa '{tipo_tarefa}': {e}")
            # --- FIM DA MODIFICAÇÃO ---
            # 3. Concatenar instrucoes_extras ao final do prompt
            instrucoes_extras = job_data.get('instrucoes_extras') or ''
            prompt_final = prompt_principal.strip()
            if instrucoes_extras:
                prompt_final += '\n\n' + instrucoes_extras.strip()
            # 4. Enviar para LLM
            model_para_etapa = job_data.get('model_name')
            llm_provider = create_provider(model_name=model_para_etapa, user_email=usuario_executor, group_resolver=self.group_resolver)
            # O provider deve aceitar o prompt concatenado
            llm_response = llm_provider.invoke(prompt_final)
            # 5. Salvar e retornar relatório gerado
            job_info['data']['analysis_report'] = llm_response
            url = self.report_handler.save_report_to_blob(job_id, job_info, llm_response)
            job_info['data']['report_blob_url'] = url
            self.job_handler.update_job(job_id, job_info)
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
