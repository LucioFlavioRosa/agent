import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from agents.agente_revisor import AgenteRevisor


class TestAgenteRevisor:
    
    def setup_method(self):
        self.mock_repository_reader = Mock()
        self.mock_llm_provider = Mock()
        
        with patch('agents.agente_revisor.init_logger'):
            self.agente = AgenteRevisor(self.mock_repository_reader, self.mock_llm_provider)
    
    def test_init_with_valid_providers(self):
        assert self.agente.repository_reader == self.mock_repository_reader
        assert self.agente.llm_provider == self.mock_llm_provider
    
    def test_init_with_none_providers_raises_error(self):
        with pytest.raises(TypeError):
            AgenteRevisor(None, None)
    
    def test_get_code_success(self):
        expected_code = {"file1.py": "content1", "file2.py": "content2"}
        self.mock_repository_reader.read_repository.return_value = expected_code
        
        result = self.agente._get_code(
            repositorio="test/repo",
            nome_branch="main",
            tipo_analise="test_analysis",
            repository_type="github"
        )
        
        assert result == expected_code
        self.mock_repository_reader.read_repository.assert_called_once_with(
            nome_repo="test/repo",
            tipo_analise="test_analysis",
            repository_type="github",
            nome_branch="main",
            arquivos_especificos=None
        )
    
    def test_get_code_with_specific_files(self):
        expected_code = {"specific.py": "specific_content"}
        self.mock_repository_reader.read_repository.return_value = expected_code
        
        result = self.agente._get_code(
            repositorio="test/repo",
            nome_branch="feature",
            tipo_analise="test_analysis",
            repository_type="gitlab",
            arquivos_especificos=["specific.py"]
        )
        
        assert result == expected_code
        self.mock_repository_reader.read_repository.assert_called_once_with(
            nome_repo="test/repo",
            tipo_analise="test_analysis",
            repository_type="gitlab",
            nome_branch="feature",
            arquivos_especificos=["specific.py"]
        )
    
    def test_get_code_repository_exception(self):
        self.mock_repository_reader.read_repository.side_effect = Exception("Repository error")
        
        with pytest.raises(RuntimeError, match="Falha ao ler o repositório: Repository error"):
            self.agente._get_code(
                repositorio="test/repo",
                nome_branch="main",
                tipo_analise="test_analysis",
                repository_type="github"
            )
    
    @patch('agents.agente_revisor.log_custom_data')
    def test_main_success_with_code(self, mock_log):
        test_code = {"file1.py": "print('hello')"}
        self.mock_repository_reader.read_repository.return_value = test_code
        self.mock_llm_provider.executar_prompt.return_value = {
            'reposta_final': 'analysis_result',
            'tokens_entrada': 100,
            'tokens_saida': 200
        }
        
        result = self.agente.main(
            tipo_analise="test_analysis",
            repositorio="test/repo",
            repository_type="github",
            job_id="test-job-123",
            projeto="test-project"
        )
        
        assert result == {"resultado": {"reposta_final": {
            'reposta_final': 'analysis_result',
            'tokens_entrada': 100,
            'tokens_saida': 200
        }}}
        
        assert mock_log.call_count == 2
    
    @patch('agents.agente_revisor.log_custom_data')
    def test_main_no_code_found(self, mock_log):
        self.mock_repository_reader.read_repository.return_value = {}
        
        result = self.agente.main(
            tipo_analise="test_analysis",
            repositorio="test/repo",
            repository_type="github",
            job_id="test-job-123",
            projeto="test-project"
        )
        
        assert result == {"resultado": {"reposta_final": {}}}
        
        mock_log.assert_called_with(
            job_id="test-job-123",
            projeto="test-project",
            status="ERRO_SEM_CODIGO",
            repositorio="test/repo",
            tipo_analise="test_analysis",
            data_hora=mock_log.call_args[1]['data_hora']
        )
    
    @patch('agents.agente_revisor.log_custom_data')
    def test_main_no_specific_files_found(self, mock_log):
        self.mock_repository_reader.read_repository.return_value = {}
        
        result = self.agente.main(
            tipo_analise="test_analysis",
            repositorio="test/repo",
            repository_type="github",
            arquivos_especificos=["missing.py"],
            job_id="test-job-123",
            projeto="test-project"
        )
        
        assert result == {"resultado": {"reposta_final": {}}}
    
    def test_main_with_all_parameters(self):
        test_code = {"complex.py": "complex_code"}
        self.mock_repository_reader.read_repository.return_value = test_code
        self.mock_llm_provider.executar_prompt.return_value = {
            'reposta_final': 'complex_analysis',
            'tokens_entrada': 500,
            'tokens_saida': 1000
        }
        
        with patch('agents.agente_revisor.log_custom_data'):
            result = self.agente.main(
                tipo_analise="complex_analysis",
                repositorio="complex/repo",
                repository_type="azure",
                nome_branch="feature/complex",
                instrucoes_extras="detailed instructions",
                usar_rag=True,
                model_name="advanced-model",
                max_token_out=25000,
                arquivos_especificos=["complex.py"],
                job_id="complex-job-456",
                projeto="complex-project",
                status_update="processing"
            )
        
        expected_call_args = {
            'tipo_tarefa': 'complex_analysis',
            'prompt_principal': json.dumps(test_code, indent=2, ensure_ascii=False),
            'instrucoes_extras': 'detailed instructions',
            'usar_rag': True,
            'model_name': 'advanced-model',
            'max_token_out': 25000
        }
        
        self.mock_llm_provider.executar_prompt.assert_called_once_with(**expected_call_args)
        assert result["resultado"]["reposta_final"]['reposta_final'] == 'complex_analysis'
    
    def test_main_llm_provider_exception(self):
        test_code = {"file.py": "code"}
        self.mock_repository_reader.read_repository.return_value = test_code
        self.mock_llm_provider.executar_prompt.side_effect = Exception("LLM Error")
        
        with pytest.raises(Exception, match="LLM Error"):
            self.agente.main(
                tipo_analise="test_analysis",
                repositorio="test/repo",
                repository_type="github"
            )
    
    def test_main_with_unicode_and_special_chars(self):
        test_code = {"unicode.py": "# 测试文件\nprint('🚀')"}
        self.mock_repository_reader.read_repository.return_value = test_code
        self.mock_llm_provider.executar_prompt.return_value = {
            'reposta_final': 'unicode_analysis',
            'tokens_entrada': 150,
            'tokens_saida': 300
        }
        
        with patch('agents.agente_revisor.log_custom_data'):
            result = self.agente.main(
                tipo_analise="unicode_analysis",
                repositorio="unicode/repo",
                repository_type="github"
            )
        
        call_args = self.mock_llm_provider.executar_prompt.call_args[1]
        assert "测试文件" in call_args['prompt_principal']
        assert "🚀" in call_args['prompt_principal']
        assert result["resultado"]["reposta_final"]['reposta_final'] == 'unicode_analysis'