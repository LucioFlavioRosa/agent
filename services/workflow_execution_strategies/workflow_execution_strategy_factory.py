from services.workflow_execution_strategies.default_workflow_strategy import DefaultWorkflowStrategy
from services.workflow_execution_strategies.epic_generation_workflow_strategy import EpicGenerationWorkflowStrategy
from services.workflow_execution_strategies.incremental_workflow_strategy import IncrementalWorkflowStrategy

class WorkflowExecutionStrategyFactory:
    _strategy_registry = {
        'geracao_epicos_a_partir_de_reuniao': EpicGenerationWorkflowStrategy,
        'default': DefaultWorkflowStrategy,
        'incremental': IncrementalWorkflowStrategy
    }

    @staticmethod
    def create_strategy(job_info, job_handler, report_handler, epic_and_task_creation_service, commit_and_build_service, incremental_step_executor_service, llm_provider_factory):
        analysis_type = job_info['data'].get('original_analysis_type')
        executar_incremental = job_info['data'].get('executar_incremental', False) or job_info['data'].get('EXECUTAR_STEPS_INCREMENTALMENTE', False)
        if analysis_type == 'geracao_epicos_a_partir_de_reuniao':
            return WorkflowExecutionStrategyFactory._strategy_registry['geracao_epicos_a_partir_de_reuniao'](
                job_handler, report_handler, epic_and_task_creation_service
            )
        if executar_incremental:
            return WorkflowExecutionStrategyFactory._strategy_registry['incremental'](
                job_handler, report_handler, incremental_step_executor_service, commit_and_build_service
            )
        return WorkflowExecutionStrategyFactory._strategy_registry['default'](
            job_handler, report_handler, commit_and_build_service, llm_provider_factory
        )
