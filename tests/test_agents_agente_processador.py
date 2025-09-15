import pytest
import json
from unittest.mock import Mock, MagicMock
from agents.agente_processador import AgenteProcessador


class TestAgenteProcessador:
    
    def setup_method(self):
        self.mock_llm_provider = Mock()
        self.agente = AgenteProcessador(self.mock_llm_provider)
    
    def test_init_with_valid_provider(self):
        assert self.agente.llm_provider == self.mock_llm_provider
    
    def test_init_with_none_provider_raises_error(self):
        with pytest.raises(TypeError):
            AgenteProcessador(None)
    
    def test_main_with_valid_parameters(self):
        self.mock_llm_provider.executar_prompt.return_value = {"resultado": {"reposta_final": "test_response"}}
        
        codigo = {"test": "data"}
        result = self.agente.main(
            tipo_analise="test_analysis",
            codigo=codigo,
            repository_type="github"
        )
        
        assert result == {"resultado": {"reposta_final": "test_response"}}
        self.mock_llm_provider.executar_prompt.assert_called_once()
    
    def test_main_with_empty_codigo(self):
        self.mock_llm_provider.executar_prompt.return_value = {"resultado": {"reposta_final": "empty_response"}}
        
        result = self.agente.main(
            tipo_analise="test_analysis",
            codigo={},
            repository_type="github"
        )
        
        assert result == {"resultado": {"reposta_final": "empty_response"}}
    
    def test_main_with_none_codigo_raises_error(self):
        with pytest.raises(TypeError):
            self.agente.main(
                tipo_analise="test_analysis",
                codigo=None,
                repository_type="github"
            )
    
    def test_main_with_invalid_repository_type(self):
        self.mock_llm_provider.executar_prompt.return_value = {"resultado": {"reposta_final": "test_response"}}
        
        result = self.agente.main(
            tipo_analise="test_analysis",
            codigo={"test": "data"},
            repository_type="invalid_type"
        )
        
        assert result == {"resultado": {"reposta_final": "test_response"}}
    
    def test_main_with_all_optional_parameters(self):
        self.mock_llm_provider.executar_prompt.return_value = {"resultado": {"reposta_final": "full_response"}}
        
        codigo = {"complex": {"nested": "data"}}
        result = self.agente.main(
            tipo_analise="complex_analysis",
            codigo=codigo,
            repository_type="gitlab",
            repositorio="test/repo",
            nome_branch="feature/test",
            instrucoes_extras="extra instructions",
            usar_rag=True,
            model_name="test-model",
            max_token_out=20000
        )
        
        expected_call_args = {
            'tipo_tarefa': 'complex_analysis',
            'prompt_principal': json.dumps(codigo, indent=2, ensure_ascii=False),
            'instrucoes_extras': 'extra instructions',
            'usar_rag': True,
            'model_name': 'test-model',
            'max_token_out': 20000
        }
        
        self.mock_llm_provider.executar_prompt.assert_called_once_with(**expected_call_args)
        assert result == {"resultado": {"reposta_final": "full_response"}}
    
    def test_main_json_serialization_error(self):
        class NonSerializable:
            pass
        
        with pytest.raises(TypeError):
            self.agente.main(
                tipo_analise="test_analysis",
                codigo={"obj": NonSerializable()},
                repository_type="github"
            )
    
    def test_main_llm_provider_exception(self):
        self.mock_llm_provider.executar_prompt.side_effect = Exception("LLM Error")
        
        with pytest.raises(Exception, match="LLM Error"):
            self.agente.main(
                tipo_analise="test_analysis",
                codigo={"test": "data"},
                repository_type="github"
            )
    
    def test_main_with_unicode_content(self):
        self.mock_llm_provider.executar_prompt.return_value = {"resultado": {"reposta_final": "unicode_response"}}
        
        codigo = {"unicode": "测试数据", "emoji": "🚀"}
        result = self.agente.main(
            tipo_analise="unicode_analysis",
            codigo=codigo,
            repository_type="github"
        )
        
        assert result == {"resultado": {"reposta_final": "unicode_response"}}
        
        call_args = self.mock_llm_provider.executar_prompt.call_args[1]
        assert "测试数据" in call_args['prompt_principal']
        assert "🚀" in call_args['prompt_principal']