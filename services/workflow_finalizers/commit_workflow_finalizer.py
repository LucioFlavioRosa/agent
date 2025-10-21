from services.workflow_finalizers.workflow_finalizer_interface import IWorkflowFinalizer
from services.incremental_step_executor_service import IncrementalStepExecutorService

class CommitWorkflowFinalizer(IWorkflowFinalizer):
    def __init__(self, data_formatter, job_handler, commit_handler, dotnet_build_service=None):
        self.data_formatter = data_formatter
        self.job_handler = job_handler
        self.commit_handler = commit_handler
        self.dotnet_build_service = dotnet_build_service

    def finalize(self, job_id, job_info, workflow, final_result, repository_type, repo_name):
        executar_incremental = job_info['data'].get('executar_steps_incrementalmente', False)
        if executar_incremental and 'batch_results' in job_info['data']:
            batch_results = job_info['data']['batch_results']
            total_batches = len(batch_results)
            total_steps = sum(len(batch) if isinstance(batch, list) else 1 for batch in batch_results)
            print(f"[{job_id}] [INCREMENTAL] Finalizando workflow incremental. Batches processados: {total_batches}, Steps executados: {total_steps}.")
            final_result = IncrementalStepExecutorService.merge_all_batches(batch_results)
        dados_finais_formatados = self.data_formatter.format_incremental_result_for_commit(final_result)
        self.job_handler.update_job_status(job_id, 'committing_to_github')
        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
        print(f"[{job_id}] [DEBUG] Após execute_commits: executar_build_dotnet={job_info['data'].get('executar_build_dotnet')}, commit_details presente: {bool(job_info['data'].get('commit_details'))}")
        if job_info['data'].get('executar_build_dotnet', False):
            commit_details = job_info['data'].get('commit_details', [])
            build_errors = []
            for idx, commit in enumerate(commit_details):
                if 'build_result' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_result ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                if 'build_errors' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_errors ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                errors = commit.get('build_errors')
                if errors:
                    build_errors.extend(errors)
            if build_errors:
                job_info['data']['build_errors'] = build_errors
            else:
                job_info['data']['build_errors'] = None
            self.job_handler.update_job(job_id, job_info)
        else:
            job_info['data']['build_errors'] = None
        self.job_handler.update_job(job_id, job_info)
        print(f"[{job_id}] DIAGNÓSTICO - Job atualizado no job store")
        if job_info['data'].get('executar_build_dotnet', False):
            commit_details = job_info['data'].get('commit_details', [])
            for idx, commit in enumerate(commit_details):
                if 'build_result' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_result ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                if 'build_errors' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_errors ausente no commit_details[{idx}] quando executar_build_dotnet=True")
        self.job_handler.update_job_status(job_id, 'completed')
