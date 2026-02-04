from typing import Any, Dict
from services.report_handler import ReportHandler
from tools.prompt_utils import carregar_prompt
from services.factories.llm_provider_factory import create_provider

class SimplifiedWorkflowService:
    def __init__(self, blob_storage=None, cache_service=None, group_resolver=None):
        self.jobs = {}
        self.reports = {}
        self.blob_storage = blob_storage
        self.cache_service = cache_service
        self.group_resolver = group_resolver
        self.report_handler = ReportHandler(blob_storage, cache_service=cache_service, group_resolver=group_resolver)

    def start_analysis(self, payload: Any) -> Dict[str, Any]:
        # 1. Gera o job_id
        job_id = f"job_{len(self.jobs)+1}"
        # 2. Busca no blob storage se existe relatório com mesmo analysis_name
        projeto = getattr(payload, 'projeto', None)
        analysis_type = getattr(payload, 'analysis_type', None)
        repository_type = getattr(payload, 'repository_type', None)
        repo_name = getattr(payload, 'repo_name', None)
        branch_name = getattr(payload, 'branch_name', None)
        analysis_name = getattr(payload, 'analysis_name', None)
        usuario_executor = getattr(payload, 'usuario_executor', None)
        arquivos_especificos = getattr(payload, 'arquivos_especificos', None)
        instrucoes_extras = getattr(payload, 'instrucoes_extras', None)
        gerar_relatorio_apenas = getattr(payload, 'gerar_relatorio_apenas', None)
        retornar_lista_arquivos = getattr(payload, 'retornar_lista_arquivos', None)
        # 3. Verifica relatório existente
        report_text = self.report_handler.check_existing_report(
            projeto=projeto,
            analysis_type=analysis_type,
            repository_type=repository_type,
            repo_name=repo_name,
            branch_name=branch_name,
            analysis_name=analysis_name,
            user_email=usuario_executor
        )
        if report_text:
            # 4. Se existir, retorna o relatório existente
            self.jobs[job_id] = {
                'status': 'completed',
                'repository_type': repository_type,
                'repo_name': repo_name,
                'branch_name': branch_name,
                'analysis_type': analysis_type,
                'arquivos_especificos': arquivos_especificos,
                'instrucoes_extras': instrucoes_extras,
                'projeto': projeto,
                'analysis_name': analysis_name,
                'gerar_relatorio_apenas': gerar_relatorio_apenas,
                'retornar_lista_arquivos': retornar_lista_arquivos,
                'usuario_executor': usuario_executor,
                'report_url': None,
                'analysis_report': report_text
            }
            self.reports[job_id] = self.jobs[job_id]
            return {
                'job_id': job_id,
                'status': 'completed',
                'analysis_report': report_text
            }
        # 5. Não existe relatório, carrega prompt
        prompt_tipo = analysis_type if analysis_type else 'default'
        try:
            prompt_base = carregar_prompt(prompt_tipo)
        except Exception:
            prompt_base = ""
        # 6. Junta prompt com instrucoes_extras
        if instrucoes_extras:
            prompt_final = f"{prompt_base}\n\n{instrucoes_extras}"
        else:
            prompt_final = prompt_base
        # 7. Envia para LLM
        llm_provider = create_provider(model_name=None, user_email=usuario_executor, group_resolver=self.group_resolver)
        llm_response = llm_provider.invoke(prompt_final)
        report_text = llm_response if isinstance(llm_response, str) else str(llm_response)
        # 8. Salva job e relatório
        self.jobs[job_id] = {
            'status': 'completed',
            'repository_type': repository_type,
            'repo_name': repo_name,
            'branch_name': branch_name,
            'analysis_type': analysis_type,
            'arquivos_especificos': arquivos_especificos,
            'instrucoes_extras': instrucoes_extras,
            'projeto': projeto,
            'analysis_name': analysis_name,
            'gerar_relatorio_apenas': gerar_relatorio_apenas,
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'usuario_executor': usuario_executor,
            'report_url': None,
            'analysis_report': report_text
        }
        self.reports[job_id] = self.jobs[job_id]
        return {
            'job_id': job_id,
            'status': 'completed',
            'analysis_report': report_text
        }

    def run_analysis(self, job_id: str):
        # Mantém compatibilidade, mas não é mais chamado na primeira operação
        job = self.jobs.get(job_id)
        if not job:
            return
        job['status'] = 'processing'
        job['analysis_report'] = f"Análise concluída para o job {job_id}"
        job['report_url'] = f"http://localhost/reports/{job_id}"
        job['status'] = 'completed'
        self.reports[job_id] = job

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }

    def get_report(self, job_id: str) -> Dict[str, Any]:
        job = self.reports.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }
