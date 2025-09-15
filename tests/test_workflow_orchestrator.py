import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.workflow_orchestrator import WorkflowOrchestrator


class TestWorkflowOrchestrator:
    
    def setup_method(self):
        self.job_manager = Mock()
        self.blob_storage = Mock()
        self.workflow_registry = {
            'analysis_type_1': {
                'steps': [
                    {
                        'agent_type': 'revisor',
                        'status_update': 'analyzing',
                        'requires_approval': True,
                        'params': {}
                    },
                    {
                        'agent_type': 'processador',
                        'status_update': 'processing',
                        'requires_approval': False,
                        'params': {}
                    }
                ]
            }
        }
        
        with patch('services.workflow_orchestrator.AzureAISearchRAGRetriever'), \
             patch('services.workflow_orchestrator.ChangesetFiller'):
            self.orchestrator = WorkflowOrchestrator(
                self.job_manager, 
                self.blob_storage, 
                self.workflow_registry
            )
    
    def test_execute_workflow_job_not_found_raises(self):
        self.job_manager.get_job.return_value = None
        
        with pytest.raises(ValueError, match="Job não encontrado"):
            self.orchestrator.execute_workflow("non_existent_job")
    
    def test_execute_workflow_workflow_not_found_raises(self):
        job_info = {
            'data': {
                'original_analysis_type': 'unknown_type',
                'repository_type': 'github',
                'repo_name': 'test_repo'
            }
        }
        self.job_manager.get_job.return_value = job_info
        
        with pytest.raises(ValueError, match="Workflow não encontrado"):
            self.orchestrator.execute_workflow("test_job")
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ReaderGeral')
    @patch('services.workflow_orchestrator.LLMProviderFactory')
    @patch('services.workflow_orchestrator.AgentFactory')
    def test_execute_workflow_report_only_mode(self, mock_agent_factory, mock_llm_factory, 
                                             mock_reader, mock_repo_provider):
        job_info = {
            'data': {
                'original_analysis_type': 'analysis_type_1',
                'repository_type': 'github',
                'repo_name': 'test_repo',
                'gerar_relatorio_apenas': True,
                'gerar_novo_relatorio': True,
                'instrucoes_extras': 'test instructions',
                'analysis_name': 'test_analysis',
                'projeto': 'test_project',
                'branch_name': 'main'
            }
        }
        
        mock_agent = Mock()
        mock_agent.main.return_value = {
            'resultado': {
                'reposta_final': {
                    'reposta_final': json.dumps({'relatorio': 'Test report content'})
                }
            }
        }
        mock_agent_factory.create_agent.return_value = mock_agent
        
        self.job_manager.get_job.return_value = job_info
        self.blob_storage.upload_report.return_value = 'http://blob.url'
        
        self.orchestrator.execute_workflow("test_job")
        
        self.job_manager.update_job_status.assert_called_with("test_job", 'completed')
        self.blob_storage.upload_report.assert_called_once()
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ReaderGeral')
    def test_execute_workflow_existing_report_blob(self, mock_reader, mock_repo_provider):
        job_info = {
            'data': {
                'original_analysis_type': 'analysis_type_1',
                'repository_type': 'github',
                'repo_name': 'test_repo',
                'gerar_novo_relatorio': False,
                'gerar_relatorio_apenas': True,
                'analysis_name': 'existing_analysis',
                'projeto': 'test_project',
                'branch_name': 'main'
            }
        }
        
        existing_report_content = 'Existing report from blob storage'
        self.job_manager.get_job.return_value = job_info
        self.blob_storage.read_report.return_value = existing_report_content
        self.blob_storage.get_report_url.return_value = 'http://existing.blob.url'
        
        self.orchestrator.execute_workflow("test_job")
        
        self.blob_storage.read_report.assert_called_once()
        self.job_manager.update_job_status.assert_called_with("test_job", 'completed')
        assert job_info['data']['analysis_report'] == existing_report_content
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ReaderGeral')
    @patch('services.workflow_orchestrator.LLMProviderFactory')
    @patch('services.workflow_orchestrator.AgentFactory')
    def test_execute_workflow_requires_approval_pauses(self, mock_agent_factory, mock_llm_factory,
                                                      mock_reader, mock_repo_provider):
        job_info = {
            'data': {
                'original_analysis_type': 'analysis_type_1',
                'repository_type': 'github',
                'repo_name': 'test_repo',
                'gerar_novo_relatorio': True,
                'instrucoes_extras': 'test instructions',
                'analysis_name': 'test_analysis',
                'projeto': 'test_project',
                'branch_name': 'main'
            }
        }
        
        mock_agent = Mock()
        mock_agent.main.return_value = {
            'resultado': {
                'reposta_final': {
                    'reposta_final': json.dumps({'relatorio': 'Test report for approval'})
                }
            }
        }
        mock_agent_factory.create_agent.return_value = mock_agent
        
        self.job_manager.get_job.return_value = job_info
        self.blob_storage.upload_report.return_value = 'http://blob.url'
        
        self.orchestrator.execute_workflow("test_job")
        
        assert job_info['status'] == 'pending_approval'
        assert job_info['data']['paused_at_step'] == 0
        self.job_manager.update_job.assert_called_with("test_job", job_info)
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ReaderGeral')
    @patch('services.workflow_orchestrator.LLMProviderFactory')
    @patch('services.workflow_orchestrator.AgentFactory')
    def test_execute_step_agent_type_unknown_raises(self, mock_agent_factory, mock_llm_factory,
                                                   mock_reader, mock_repo_provider):
        job_info = {
            'data': {
                'repository_type': 'github',
                'instrucoes_extras': 'test instructions'
            }
        }
        
        step = {
            'agent_type': 'unknown_agent_type',
            'params': {}
        }
        
        with pytest.raises(ValueError, match="Tipo de agente desconhecido 'unknown_agent_type'"):
            self.orchestrator._execute_step(
                "test_job", job_info, step, 0, {}, mock_reader.return_value, 0, 0
            )
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ReaderGeral')
    @patch('services.workflow_orchestrator.LLMProviderFactory')
    @patch('services.workflow_orchestrator.AgentFactory')
    def test_execute_step_agent_response_empty_reuses_previous(self, mock_agent_factory, mock_llm_factory,
                                                             mock_reader, mock_repo_provider):
        job_info = {
            'data': {
                'repository_type': 'github',
                'instrucoes_extras': 'test instructions'
            }
        }
        
        step = {
            'agent_type': 'processador',
            'params': {}
        }
        
        previous_result = {'previous': 'result'}
        
        mock_agent = Mock()
        mock_agent.main.return_value = {
            'resultado': {
                'reposta_final': {
                    'reposta_final': ''
                }
            }
        }
        mock_agent_factory.create_agent.return_value = mock_agent
        
        result = self.orchestrator._execute_step(
            "test_job", job_info, step, 1, previous_result, mock_reader.return_value, 0, 0
        )
        
        assert result == previous_result
    
    def test_save_report_to_blob_skips_when_flag_false(self):
        job_info = {
            'data': {
                'gerar_novo_relatorio': False,
                'analysis_name': 'test_analysis'
            }
        }
        
        self.orchestrator._save_report_to_blob(
            "test_job", job_info, "test report", True
        )
        
        self.blob_storage.upload_report.assert_not_called()
    
    @patch('services.workflow_orchestrator.get_repository_provider_explicit')
    @patch('services.workflow_orchestrator.ConexaoGeral')
    @patch('services.workflow_orchestrator.processar_branch_por_provedor')
    def test_execute_commits_multiple_groups(self, mock_processar_branch, mock_conexao, mock_repo_provider):
        job_info = {
            'data': {
                'branch_name': 'main'
            }
        }
        
        dados_finais = {
            'grupos': [
                {
                    'branch_sugerida': 'feature/branch1',
                    'titulo_pr': 'PR Title 1',
                    'resumo_do_pr': 'PR Description 1',
                    'conjunto_de_mudancas': [{'file': 'test1.py'}]
                },
                {
                    'branch_sugerida': 'feature/branch2',
                    'titulo_pr': 'PR Title 2',
                    'resumo_do_pr': 'PR Description 2',
                    'conjunto_de_mudancas': [{'file': 'test2.py'}]
                }
            ]
        }
        
        mock_repo = Mock()
        mock_conexao.create_with_defaults.return_value.connection.return_value = mock_repo
        mock_processar_branch.return_value = {'status': 'success'}
        
        self.orchestrator._execute_commits(
            "test_job", job_info, dados_finais, 'github', 'test_repo'
        )
        
        assert mock_processar_branch.call_count == 2
        assert job_info['data']['commit_details'] == [{'status': 'success'}, {'status': 'success'}]
    
    def test_format_final_data_handles_empty_and_multiple_groups(self):
        dados_preenchidos_empty = {
            'resumo_geral': 'General summary'
        }
        
        result_empty = self.orchestrator._format_final_data(dados_preenchidos_empty)
        
        expected_empty = {
            'resumo_geral': 'General summary',
            'grupos': []
        }
        
        assert result_empty == expected_empty
        
        dados_preenchidos_multiple = {
            'resumo_geral': 'General summary',
            'group1': {
                'resumo_do_pr': 'PR Summary 1',
                'descricao_do_pr': 'PR Description 1',
                'conjunto_de_mudancas': [{'file': 'test1.py'}]
            },
            'group2': {
                'resumo_do_pr': 'PR Summary 2',
                'descricao_do_pr': 'PR Description 2',
                'conjunto_de_mudancas': [{'file': 'test2.py'}]
            }
        }
        
        result_multiple = self.orchestrator._format_final_data(dados_preenchidos_multiple)
        
        expected_multiple = {
            'resumo_geral': 'General summary',
            'grupos': [
                {
                    'branch_sugerida': 'group1',
                    'titulo_pr': 'PR Summary 1',
                    'resumo_do_pr': 'PR Description 1',
                    'conjunto_de_mudancas': [{'file': 'test1.py'}]
                },
                {
                    'branch_sugerida': 'group2',
                    'titulo_pr': 'PR Summary 2',
                    'resumo_do_pr': 'PR Description 2',
                    'conjunto_de_mudancas': [{'file': 'test2.py'}]
                }
            ]
        }
        
        assert result_multiple == expected_multiple
