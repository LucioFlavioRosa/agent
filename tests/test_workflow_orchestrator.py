import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from services.workflow_orchestrator import WorkflowOrchestrator

class TestWorkflowOrchestrator:
    
    @pytest.fixture
    def mock_dependencies(self):
        """Cria mocks para todas as dependências do WorkflowOrchestrator."""
        job_manager = Mock()
        blob_storage = Mock()
        workflow_registry = {
            'test_analysis': {
                'steps': [
                    {
                        'agent_type': 'revisor',
                        'status_update': 'analyzing',
                        'requires_approval': True,
                        'params': {}
                    }
                ]
            }
        }
        return job_manager, blob_storage, workflow_registry
    
    @pytest.fixture
    def orchestrator(self, mock_dependencies):
        """Cria uma instância do WorkflowOrchestrator com dependências mockadas."""
        job_manager, blob_storage, workflow_registry = mock_dependencies
        return WorkflowOrchestrator(job_manager, blob_storage, workflow_registry)
    
    def test_try_read_existing_report_when_gerar_novo_relatorio_true(self, orchestrator):
        """Testa que não tenta ler relatório existente quando gerar_novo_relatorio é True."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': True,
                'analysis_name': 'test-analysis'
            }
        }
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 0)
        
        assert result is None
        orchestrator.blob_storage.read_report.assert_not_called()
    
    def test_try_read_existing_report_when_gerar_novo_relatorio_false_and_report_exists(self, orchestrator):
        """Testa que lê relatório existente quando gerar_novo_relatorio é False e relatório existe."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main'
            }
        }
        
        # Mock do blob storage retornando um relatório existente
        orchestrator.blob_storage.read_report.return_value = "Relatório existente do blob storage"
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 0)
        
        assert result is not None
        assert 'resultado' in result
        assert 'reposta_final' in result['resultado']
        
        # Verifica se o blob storage foi chamado com os parâmetros corretos
        orchestrator.blob_storage.read_report.assert_called_once_with(
            'test-project',
            'test_analysis',
            'github',
            'test/repo',
            'main',
            'test-analysis'
        )
        
        # Verifica se o resultado contém o relatório
        parsed_result = json.loads(result['resultado']['reposta_final']['reposta_final'])
        assert parsed_result['relatorio'] == "Relatório existente do blob storage"
    
    def test_try_read_existing_report_when_gerar_novo_relatorio_false_and_report_not_exists(self, orchestrator):
        """Testa que retorna None quando gerar_novo_relatorio é False mas relatório não existe."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main'
            }
        }
        
        # Mock do blob storage retornando None (relatório não encontrado)
        orchestrator.blob_storage.read_report.return_value = None
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 0)
        
        assert result is None
        orchestrator.blob_storage.read_report.assert_called_once()
    
    def test_try_read_existing_report_when_analysis_name_missing(self, orchestrator):
        """Testa que retorna None quando analysis_name não é fornecido."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': None
            }
        }
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 0)
        
        assert result is None
        orchestrator.blob_storage.read_report.assert_not_called()
    
    def test_try_read_existing_report_when_not_step_zero(self, orchestrator):
        """Testa que retorna None quando não é a etapa 0."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis'
            }
        }
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 1)
        
        assert result is None
        orchestrator.blob_storage.read_report.assert_not_called()
    
    def test_try_read_existing_report_handles_blob_storage_exception(self, orchestrator):
        """Testa que trata exceções do blob storage graciosamente."""
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main'
            }
        }
        
        # Mock do blob storage levantando uma exceção
        orchestrator.blob_storage.read_report.side_effect = Exception("Erro de conexão")
        
        result = orchestrator._try_read_existing_report('job-123', job_info, 0)
        
        assert result is None
        orchestrator.blob_storage.read_report.assert_called_once()