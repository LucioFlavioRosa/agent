import pytest
from unittest.mock import MagicMock, patch, call
from services.workflow_orchestrator import WorkflowOrchestrator
from models import JobFields

@pytest.fixture
def job_manager():
    return MagicMock()

@pytest.fixture
def blob_storage():
    return MagicMock()

@pytest.fixture
def workflow_registry():
    return {
        'dummy_analysis': {
            'steps': [
                {
                    'status_update': 'step_0',
                    'model_name': 'gpt-4',
                    'agent': 'dummy',
                    'params': {}
                },
                {
                    'status_update': 'step_1',
                    'model_name': 'gpt-4',
                    'agent': 'dummy',
                    'params': {}
                }
            ]
        }
    }

@pytest.fixture
def job_info():
    return {
        'data': {
            'original_analysis_type': 'dummy_analysis',
            'repository_type': 'github',
            'repo_name': 'repo',
            'repo_name_modernizado': 'repo',
            'branch_name_modernizado': 'main',
            'repo_name_original': 'repo_orig',
            'branch_name_original': 'main',
            'retornar_lista_arquivos': False,
            'usar_rag': False,
            'model_name': 'gpt-4',
            'modo_adicao_incremental': False,
            'usuario_executor': None,
            'gerar_relatorio_apenas': False,
            'gerar_novo_relatorio': True,
            'analysis_report': None,
            'report_blob_url': None
        },
        'status': 'pending',
        'step_results': {}
    }

@pytest.fixture
def orchestrator(job_manager, blob_storage, workflow_registry):
    mock_rag_retriever = MagicMock()
    return WorkflowOrchestrator(
        job_manager=job_manager,
        blob_storage=blob_storage,
        workflow_registry=workflow_registry,
        rag_retriever=mock_rag_retriever
    )

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_saves_report_when_generated_by_agent(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    # Arrange
    job_id = 'job123'
    job_info['data']['gerar_novo_relatorio'] = True
    job_info['data']['gerar_relatorio_apenas'] = False
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    # Mock report_handler
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = None
    orchestrator.report_handler.extract_report_text.return_value = 'relatorio gerado'
    orchestrator.report_handler.save_report_to_blob.return_value = 'https://blob/report.md'
    # Mock strategy
    mock_strategy = MagicMock()
    mock_strategy.should_pause_for_approval.return_value = False
    mock_strategy.should_finalize_workflow.return_value = False
    mock_strategy.execute_step.return_value = {'relatorio': 'relatorio gerado'}
    mock_strategy_factory.create_strategy.return_value = mock_strategy
    # Act
    orchestrator.execute_workflow(job_id)
    # Assert
    assert job_info['data']['report_blob_url'] or orchestrator.report_handler.save_report_to_blob.called

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_finalizes_when_gerar_relatorio_apenas_is_true(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'job456'
    job_info['data']['gerar_novo_relatorio'] = True
    job_info['data']['gerar_relatorio_apenas'] = True
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = None
    orchestrator.report_handler.extract_report_text.return_value = 'relatorio gerado para finalizar'
    orchestrator.report_handler.save_report_to_blob.return_value = 'https://blob/report2.md'
    mock_strategy = MagicMock()
    mock_strategy.should_pause_for_approval.return_value = False
    mock_strategy.should_finalize_workflow.return_value = False
    mock_strategy.execute_step.return_value = {'relatorio': 'relatorio gerado para finalizar'}
    mock_strategy_factory.create_strategy.return_value = mock_strategy
    # Act
    orchestrator.execute_workflow(job_id)
    # Assert
    job_manager.update_job_status.assert_any_call(job_id, 'completed')

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_pauses_for_approval_when_strategy_requires(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'job789'
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = None
    orchestrator.report_handler.extract_report_text.return_value = 'relatorio para aprovacao'
    orchestrator.report_handler.save_report_to_blob.return_value = 'https://blob/report3.md'
    mock_strategy = MagicMock()
    mock_strategy.should_pause_for_approval.return_value = True
    mock_strategy.should_finalize_workflow.return_value = False
    mock_strategy.execute_step.return_value = {'relatorio': 'relatorio para aprovacao'}
    mock_strategy_factory.create_strategy.return_value = mock_strategy
    orchestrator.handle_approval_step = MagicMock()
    # Act
    orchestrator.execute_workflow(job_id)
    # Assert
    orchestrator.handle_approval_step.assert_called()

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_handles_exception_and_updates_job_to_failed(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'job999'
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = None
    # Simula exceção no execute_step_with_strategy
    orchestrator._execute_step_with_strategy = MagicMock(side_effect=Exception('Erro simulado'))
    # Act
    orchestrator.execute_workflow(job_id)
    # Assert
    job_manager.handle_job_error.assert_called()

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_reads_existing_report_from_blob_when_gerar_novo_relatorio_is_false(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'jobblob'
    job_info['data']['gerar_novo_relatorio'] = False
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = 'relatorio do blob'
    orchestrator.report_handler.validate_and_parse_blob_report.return_value = 'relatorio do blob'
    mock_strategy = MagicMock()
    mock_strategy.should_pause_for_approval.return_value = False
    mock_strategy.should_finalize_workflow.return_value = True
    mock_strategy_factory.create_strategy.return_value = mock_strategy
    # Act
    orchestrator.execute_workflow(job_id)
    # Assert
    assert orchestrator.report_handler.try_read_existing_report.called
    assert orchestrator.report_handler.validate_and_parse_blob_report.called
    job_manager.update_job_status.assert_any_call(job_id, 'completed')

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_execute_workflow_validates_report_before_finalizing_in_report_only_mode(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'jobempty'
    job_info['data']['gerar_relatorio_apenas'] = True
    job_manager.get_job.return_value = job_info.copy()
    job_manager.get_step_result.return_value = None
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.try_read_existing_report.return_value = None
    orchestrator.report_handler.extract_report_text.return_value = ''  # Relatório vazio
    orchestrator.report_handler.save_report_to_blob.return_value = 'https://blob/report4.md'
    mock_strategy = MagicMock()
    mock_strategy.should_pause_for_approval.return_value = False
    mock_strategy.should_finalize_workflow.return_value = False
    mock_strategy.execute_step.return_value = {'relatorio': ''}
    mock_strategy_factory.create_strategy.return_value = mock_strategy
    # Act & Assert
    with pytest.raises(ValueError, match='ERRO CRÍTICO: Tentativa de finalizar workflow no modo report_only sem relatório válido'):
        orchestrator.execute_workflow(job_id)

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_save_generated_report_returns_false_when_report_is_empty(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'jobemptyreport'
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.extract_report_text.return_value = '   '
    step_result = {'relatorio': '   '}
    result = orchestrator._save_generated_report(job_id, job_info, step_result, 0)
    assert result is False

@patch('services.workflow_orchestrator.StepStrategyFactory')
def test_save_generated_report_raises_error_when_blob_url_is_not_set(mock_strategy_factory, orchestrator, job_manager, blob_storage, workflow_registry, job_info):
    job_id = 'jobnourl'
    orchestrator.report_handler = MagicMock()
    orchestrator.report_handler.extract_report_text.return_value = 'relatorio gerado'
    orchestrator.report_handler.save_report_to_blob.return_value = None  # Simula erro
    step_result = {'relatorio': 'relatorio gerado'}
    with pytest.raises(ValueError, match='Relatório não foi salvo no Blob Storage'):
        orchestrator._save_generated_report(job_id, job_info, step_result, 0)
