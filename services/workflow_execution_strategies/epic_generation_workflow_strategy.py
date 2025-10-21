from services.workflow_execution_strategies.base_workflow_strategy import BaseWorkflowStrategy

class EpicGenerationWorkflowStrategy(BaseWorkflowStrategy):
    def __init__(self, job_handler, report_handler, epic_and_task_creation_service):
        super().__init__(job_handler, report_handler)
        self.epic_and_task_creation_service = epic_and_task_creation_service

    def execute(self, job_id, job_info, workflow, start_from_step, repo_reader):
        previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            self.job_handler.update_job_status(job_id, step['status_update'])
            strategy = None
            step_result = None
            from services.step_strategies.step_strategy_factory import StepStrategyFactory
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
            step_result = strategy.execute_step(
                job_id, job_info, step, current_step_index,
                previous_step_result, repo_reader, None, step.get('params', {})
            )
            self.job_handler.save_step_result(job_info, current_step_index, step_result)
            previous_step_result = step_result
            if strategy.should_pause_for_approval(job_info, step):
                self._handle_approval_pause(job_id, job_info, step_result, current_step_index)
                return
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        analysis_report = job_info['data'].get('analysis_report')
        organization_url = job_info['data'].get('organization_url')
        project_name = job_info['data'].get('azure_project_name')
        result = self.epic_and_task_creation_service.create_epics_and_tasks_from_report(
            job_id, job_info, analysis_report, organization_url, project_name
        )
        job_info['data']['cards_criados'] = result['cards_criados']
        job_info['data']['tarefas_criadas'] = result['tarefas_criadas']
        job_info['data']['tarefas_creation_errors'] = result['tarefas_creation_errors']
        job_info['data']['tarefas_parsing_errors'] = result['tarefas_parsing_errors']
        self.job_handler.update_job_status(job_id, 'completed')
        self.job_handler.update_job(job_id, job_info)
