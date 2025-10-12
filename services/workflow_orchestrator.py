from typing import Any, Dict
from services.commit_handler import CommitHandler
from services.job_data_service import JobDataService
from services.job_logging_service import JobLoggingService
from services.job_validation_service import JobValidationService
from services.pull_request_extractor_service import PullRequestExtractorService
from services.response_builder_service import ResponseBuilderService
from models import JobFields, JobStatus

class WorkflowOrchestrator:
    def __init__(self, commit_handler: CommitHandler, job_data_service: JobDataService, job_logging_service: JobLoggingService, job_validation_service: JobValidationService, pr_extractor_service: PullRequestExtractorService, response_builder_service: ResponseBuilderService):
        self.commit_handler = commit_handler
        self.job_data_service = job_data_service
        self.job_logging_service = job_logging_service
        self.job_validation_service = job_validation_service
        self.pr_extractor_service = pr_extractor_service
        self.response_builder_service = response_builder_service

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], repository_type: str, repo_name: str):
        print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR] Iniciando _finalize_workflow")
        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
        print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] Após execute_commits: executar_build_dotnet={job_info['data'].get('executar_build_dotnet')}, commit_details presente: {'commit_details' in job_info['data']}")
        executar_build_dotnet = job_info['data'].get('executar_build_dotnet', False)
        commit_details = job_info['data'].get('commit_details', [])
        if executar_build_dotnet:
            missing_build_fields = False
            for idx, commit in enumerate(commit_details):
                has_build_result = 'build_result' in commit
                has_build_errors = 'build_errors' in commit
                print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] Commit {idx+1}: build_result presente={has_build_result}, build_errors presente={has_build_errors}")
                if not has_build_result:
                    print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][ERRO CRÍTICO] build_result ausente em commit_details[{idx}]")
                    missing_build_fields = True
                if not has_build_errors and not (commit.get('build_result', {}).get('success', True)):
                    print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][ERRO CRÍTICO] build_errors ausente em commit_details[{idx}] para build falho")
                    missing_build_fields = True
            if missing_build_fields:
                print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][ERRO CRÍTICO] Um ou mais commits estão sem build_result/build_errors quando executar_build_dotnet=True")
        print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] Antes de consolidar build_errors de commit_details")
        build_errors = []
        for idx, commit in enumerate(commit_details):
            errors = commit.get('build_errors')
            if errors:
                print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] build_errors encontrados em commit_details[{idx}]: {errors}")
                build_errors.extend(errors)
        print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] Após consolidação: total de build_errors={len(build_errors)}")
        if build_errors:
            job_info['data']['build_errors'] = build_errors
        else:
            job_info['data']['build_errors'] = None
        print(f"[{job_id}] [WORKFLOW_ORCHESTRATOR][DEBUG] job_info['data']['build_errors'] setado para: {job_info['data']['build_errors']}")
