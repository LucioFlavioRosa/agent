from domain.interfaces.workflow_execution_strategy_interface import IWorkflowExecutionStrategy

class IncrementalWorkflowStrategy(IWorkflowExecutionStrategy):
    def __init__(self, job_handler, report_handler, incremental_step_executor_service, commit_and_build_service):
        self.job_handler = job_handler
        self.report_handler = report_handler
        self.incremental_step_executor_service = incremental_step_executor_service
        self.commit_and_build_service = commit_and_build_service

    def execute(self, job_id, job_info, workflow, start_from_step, repo_reader):
        batch_results = self.incremental_step_executor_service.execute_incremental_workflow(job_id, job_info, workflow, start_from_step, repo_reader)
        final_result = self.incremental_step_executor_service.merge_all_batches(batch_results)
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        self.commit_and_build_service.execute_commits_and_builds(job_id, job_info, final_result, repository_type, repo_name)
        self.job_handler.update_job_status(job_id, 'completed')
        self.job_handler.update_job(job_id, job_info)
