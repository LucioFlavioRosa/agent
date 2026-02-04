import pytest
from unittest.mock import patch
from tools import prompt_utils

@patch("builtins.open", create=True)
@patch("os.path.isfile")
def test_prompt_loading_and_concatenation(mock_isfile, mock_open):
    mock_isfile.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = "Prompt base para tarefa."

    tipo_tarefa = "melhoria_codigo"
    instrucoes_extras = "Instruções adicionais para o agente."
    prompt = prompt_utils.carregar_prompt(tipo_tarefa)
    assert prompt == "Prompt base para tarefa."

    # Simula concatenação
    resultado_final = prompt + "\n" + instrucoes_extras
    assert "Prompt base para tarefa." in resultado_final
    assert "Instruções adicionais para o agente." in resultado_final

    # Simula envio para LLM (mock)
    class FakeLLMProvider:
        def generate_report(self, texto):
            self.last_text = texto
            return "Relatório gerado"
    llm = FakeLLMProvider()
    output = llm.generate_report(resultado_final)
    assert output == "Relatório gerado"
    assert llm.last_text == resultado_final
