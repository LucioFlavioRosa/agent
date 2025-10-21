from services.workflow_finalizers.workflow_finalizer_interface import IWorkflowFinalizer

class CommitWorkflowFinalizer(IWorkflowFinalizer):
    def __init__(self, data_formatter, job_handler, commit_handler, azure_devops_service=None, dotnet_build_service=None):
        self.data_formatter = data_formatter
        self.job_handler = job_handler
        self.commit_handler = commit_handler
        self.azure_devops_service = azure_devops_service
        self.dotnet_build_service = dotnet_build_service

    def finalize(self, job_id, job_info, workflow, final_result, repository_type, repo_name):
        commit_result = self.commit_handler.commit_changes(job_id, job_info, final_result)
        job_info['data']['commit_result'] = commit_result
        self.job_handler.update_job(job_id, job_info)
        executar_build_dotnet = job_info['data'].get('executar_build_dotnet', False)
        if executar_build_dotnet and self.dotnet_build_service:
            build_result = self.dotnet_build_service.build_repository(job_id, job_info)
            job_info['data']['build_errors'] = build_result.get('errors')
            self.job_handler.update_job(job_id, job_info)
