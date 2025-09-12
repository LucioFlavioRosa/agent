import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from services.workflow_orchestrator import WorkflowOrchestrator

class TestWorkflowOrchestratorReportGeneration:
    """Testes para verificar o comportamento da flag 'gerar_novo_relatorio'."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Fixture para criar mocks das dependências."""
        job_manager = Mock()
        blob_storage = Mock()
        workflow_registry = {
            'test_analysis': {
                'steps': [
                    {
                        'agent_type': 'revisor',
                        'status_update': 'analyzing',
                        'requires_approval': False,
                        'params': {}
                    }
                ]
            }
        }
        
        orchestrator = WorkflowOrchestrator(job_manager, blob_storage, workflow_registry)
        
        return {
            'orchestrator': orchestrator,
            'job_manager': job_manager,
            'blob_storage': blob_storage,
            'workflow_registry': workflow_registry
        }
    
    def test_gerar_novo_relatorio_false_with_existing_report(self, mock_dependencies):
        """Teste: gerar_novo_relatorio=False com relatório existente deve finalizar sem gerar novo."""
        # Arrange
        orchestrator = mock_dependencies['orchestrator']
        job_manager = mock_dependencies['job_manager']
        blob_storage = mock_dependencies['blob_storage']
        
        job_id = 'test-job-123'
        job_info = {
            'status': 'starting',
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis-name',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main'
            }
        }
        
        existing_report = "Este é um relatório existente do Blob Storage"
        
        job_manager.get_job.return_value = job_info
        blob_storage.read_report.return_value = existing_report
        
        # Act
        orchestrator.execute_workflow(job_id, start_from_step=0)
        
        # Assert
        blob_storage.read_report.assert_called_once_with(
            'test-project',
            'test_analysis',
            'github',
            'test/repo',
            'main',
            'test-analysis-name'
        )
        
        # Verifica se o job foi atualizado com o relatório existente
        job_manager.update_job.assert_called_once()
        updated_job = job_manager.update_job.call_args[0][1]
        assert updated_job['status'] == 'completed'
        assert updated_job['data']['analysis_report'] == existing_report
        assert 'report_blob_url' in updated_job['data']
    
    def test_gerar_novo_relatorio_false_without_existing_report(self, mock_dependencies):
        """Teste: gerar_novo_relatorio=False sem relatório existente deve gerar novo."""
        # Arrange
        orchestrator = mock_dependencies['orchestrator']
        job_manager = mock_dependencies['job_manager']
        blob_storage = mock_dependencies['blob_storage']
        
        job_id = 'test-job-456'
        job_info = {
            'status': 'starting',
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis-name',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main',
                'instrucoes_extras': 'Gerar relatório de análise',
                'gerar_relatorio_apenas': True
            }
        }
        
        job_manager.get_job.return_value = job_info
        blob_storage.read_report.return_value = None  # Simula relatório não encontrado
        
        # Mock do agente e suas dependências
        with patch('services.workflow_orchestrator.get_repository_provider_explicit') as mock_repo_provider, \
             patch('services.workflow_orchestrator.ReaderGeral') as mock_reader, \
             patch('services.workflow_orchestrator.LLMProviderFactory') as mock_llm_factory, \
             patch('services.workflow_orchestrator.AgentFactory') as mock_agent_factory:
            
            mock_agent = Mock()
            mock_agent.main.return_value = {
                'resultado': {
                    'reposta_final': {
                        'reposta_final': json.dumps({'relatorio': 'Novo relatório gerado'})
                    }
                }
            }
            mock_agent_factory.create_agent.return_value = mock_agent
            
            # Act
            orchestrator.execute_workflow(job_id, start_from_step=0)
            
            # Assert
            blob_storage.read_report.assert_called_once()
            mock_agent.main.assert_called_once()  # Verifica que o agente foi executado
            job_manager.update_job_status.assert_called()  # Verifica que o status foi atualizado
    
    def test_gerar_novo_relatorio_true_always_generates_new(self, mock_dependencies):
        """Teste: gerar_novo_relatorio=True deve sempre gerar novo relatório."""
        # Arrange
        orchestrator = mock_dependencies['orchestrator']
        job_manager = mock_dependencies['job_manager']
        blob_storage = mock_dependencies['blob_storage']
        
        job_id = 'test-job-789'
        job_info = {
            'status': 'starting',
            'data': {
                'gerar_novo_relatorio': True,
                'analysis_name': 'test-analysis-name',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main',
                'instrucoes_extras': 'Gerar relatório de análise',
                'gerar_relatorio_apenas': True
            }
        }
        
        job_manager.get_job.return_value = job_info
        
        # Mock do agente e suas dependências
        with patch('services.workflow_orchestrator.get_repository_provider_explicit') as mock_repo_provider, \
             patch('services.workflow_orchestrator.ReaderGeral') as mock_reader, \
             patch('services.workflow_orchestrator.LLMProviderFactory') as mock_llm_factory, \
             patch('services.workflow_orchestrator.AgentFactory') as mock_agent_factory:
            
            mock_agent = Mock()
            mock_agent.main.return_value = {
                'resultado': {
                    'reposta_final': {
                        'reposta_final': json.dumps({'relatorio': 'Novo relatório gerado'})
                    }
                }
            }
            mock_agent_factory.create_agent.return_value = mock_agent
            
            # Act
            orchestrator.execute_workflow(job_id, start_from_step=0)
            
            # Assert
            blob_storage.read_report.assert_not_called()  # Não deve tentar ler relatório existente
            mock_agent.main.assert_called_once()  # Deve executar o agente
    
    def test_gerar_novo_relatorio_false_without_analysis_name(self, mock_dependencies):
        """Teste: gerar_novo_relatorio=False sem analysis_name deve gerar novo."""
        # Arrange
        orchestrator = mock_dependencies['orchestrator']
        job_manager = mock_dependencies['job_manager']
        blob_storage = mock_dependencies['blob_storage']
        
        job_id = 'test-job-no-name'
        job_info = {
            'status': 'starting',
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': None,  # Sem nome de análise
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main',
                'instrucoes_extras': 'Gerar relatório de análise',
                'gerar_relatorio_apenas': True
            }
        }
        
        job_manager.get_job.return_value = job_info
        
        # Mock do agente e suas dependências
        with patch('services.workflow_orchestrator.get_repository_provider_explicit') as mock_repo_provider, \
             patch('services.workflow_orchestrator.ReaderGeral') as mock_reader, \
             patch('services.workflow_orchestrator.LLMProviderFactory') as mock_llm_factory, \
             patch('services.workflow_orchestrator.AgentFactory') as mock_agent_factory:
            
            mock_agent = Mock()
            mock_agent.main.return_value = {
                'resultado': {
                    'reposta_final': {
                        'reposta_final': json.dumps({'relatorio': 'Novo relatório gerado'})
                    }
                }
            }
            mock_agent_factory.create_agent.return_value = mock_agent
            
            # Act
            orchestrator.execute_workflow(job_id, start_from_step=0)
            
            # Assert
            blob_storage.read_report.assert_not_called()  # Não deve tentar ler sem analysis_name
            mock_agent.main.assert_called_once()  # Deve executar o agente
    
    def test_blob_storage_error_fallback_to_generation(self, mock_dependencies):
        """Teste: Erro no Blob Storage deve fazer fallback para geração de novo relatório."""
        # Arrange
        orchestrator = mock_dependencies['orchestrator']
        job_manager = mock_dependencies['job_manager']
        blob_storage = mock_dependencies['blob_storage']
        
        job_id = 'test-job-error'
        job_info = {
            'status': 'starting',
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test-analysis-name',
                'projeto': 'test-project',
                'original_analysis_type': 'test_analysis',
                'repository_type': 'github',
                'repo_name': 'test/repo',
                'branch_name': 'main',
                'instrucoes_extras': 'Gerar relatório de análise',
                'gerar_relatorio_apenas': True
            }
        }
        
        job_manager.get_job.return_value = job_info
        blob_storage.read_report.side_effect = Exception("Erro de conexão com Blob Storage")
        
        # Mock do agente e suas dependências
        with patch('services.workflow_orchestrator.get_repository_provider_explicit') as mock_repo_provider, \
             patch('services.workflow_orchestrator.ReaderGeral') as mock_reader, \
             patch('services.workflow_orchestrator.LLMProviderFactory') as mock_llm_factory, \
             patch('services.workflow_orchestrator.AgentFactory') as mock_agent_factory:
            
            mock_agent = Mock()
            mock_agent.main.return_value = {
                'resultado': {
                    'reposta_final': {
                        'reposta_final': json.dumps({'relatorio': 'Novo relatório gerado após erro'})
                    }
                }
            }
            mock_agent_factory.create_agent.return_value = mock_agent
            
            # Act
            orchestrator.execute_workflow(job_id, start_from_step=0)
            
            # Assert
            blob_storage.read_report.assert_called_once()
            mock_agent.main.assert_called_once()  # Deve fazer fallback para geração