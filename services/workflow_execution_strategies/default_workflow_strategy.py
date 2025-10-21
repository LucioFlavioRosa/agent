from services.workflow_execution_strategies.base_workflow_strategy import BaseWorkflowStrategy
from services.step_strategies.step_strategy_factory import StepStrategyFactory

class DefaultWorkflowStrategy(BaseWorkflowStrategy):
    def __init__(self, job_handler, report_handler, commit_and_build_service, llm_provider_factory):
        super().__init__(job_handler, report_handler)
        self.commit_and_build_service = commit_and_build_service
        self.llm_provider_factory = llm_provider_factory

    def execute(self, job_id, job_info, workflow, start_from_step, repo_reader):
        previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            self.job_handler.update_job_status(job_id, step['status_update'])
            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            llm_provider = self.llm_provider_factory.create_provider(model_para_etapa, None)
            agent_params = step.get('params', {}).copy() if step.get('params') else {}
            agent_params['job_id'] = job_id
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
            step_result = strategy.execute_step(
                job_id, job_info, step, current_step_index,
                previous_step_result, repo_reader, llm_provider, agent_params
            )
            self.job_handler.save_step_result(job_info, current_step_index, step_result)
            previous_step_result = step_result
            if strategy.should_pause_for_approval(job_info, step):
                self._handle_approval_pause(job_id, job_info, step_result, current_step_index)
                return
            if strategy.should_finalize_workflow(job_info, current_step_index):
                self.job_handler.update_job_status(job_id, 'completed')
                return
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        final_result = previous_step_result
        self.commit_and_build_service.execute_commits_and_builds(job_id, job_info, final_result, repository_type, repo_name)
        self.job_handler.update_job_status(job_id, 'completed')
        self.job_handler.update_job(job_id, job_info)
