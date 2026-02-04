import pytest
import yaml
import os
from unittest.mock import patch, MagicMock

from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AmazonBedrockProvider
from tools.prompt_utils import carregar_prompt

def load_workflow_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_analysis_type_and_tipo_analise_extraction(tmp_path):
    # Cria um workflow.yaml temporário
    workflow_yaml = '''
analise_performance_eficiencia:
  description: "desc"
  extensions: [".py"]
  steps:
    - status_update: "analisando o repositório"
      model_name: "claude-sonnet-4-5"
      agent_type: "revisor"
      params:
        tipo_analise: "relatorio_performance_eficiencia"
      requires_approval: true
    - status_update: "aplicando_as_mudancas_apontadas"
      model_name: "gpt-4.1"
      agent_type: "revisor"
      params:
        tipo_analise: "aplicacao_de_mudancas"
'''
    wf_path = tmp_path / "workflows.yaml"
    wf_path.write_text(workflow_yaml, encoding='utf-8')
    workflows = load_workflow_yaml(str(wf_path))
    assert 'analise_performance_eficiencia' in workflows
    steps = workflows['analise_performance_eficiencia']['steps']
    assert steps[0]['params']['tipo_analise'] == 'relatorio_performance_eficiencia'
    assert steps[1]['params']['tipo_analise'] == 'aplicacao_de_mudancas'

@patch('tools.requisicao_openai.OpenAILLMProvider.carregar_prompt')
def test_openai_provider_prompt_loading(mock_carregar_prompt):
    mock_carregar_prompt.return_value = "PROMPT OPENAI"
    provider = OpenAILLMProvider(secret_manager=MagicMock(), user_email="lucio.rosa@peers.com", group_resolver=MagicMock())
    result = provider.executar_prompt(
        tipo_tarefa="relatorio_performance_eficiencia",
        prompt_principal="Teste principal",
        model_name="gpt-4.1"
    )
    mock_carregar_prompt.assert_called_once_with("relatorio_performance_eficiencia")

@patch('tools.prompt_utils.carregar_prompt')
def test_bedrock_provider_prompt_loading(mock_carregar_prompt):
    mock_carregar_prompt.return_value = "PROMPT BEDROCK"
    provider = AmazonBedrockProvider(secret_manager=MagicMock(), user_email="lucio.rosa@peers.com", group_resolver=MagicMock())
    # Mock boto3 client
    provider.bedrock_runtime = MagicMock()
    provider.bedrock_runtime.invoke_model.return_value = {
        'body': MagicMock(read=lambda: b'{"content": [{"text": "Resposta"}], "usage": {"input_tokens": 10, "output_tokens": 20}}')
    }
    result = provider.executar_prompt(
        tipo_tarefa="relatorio_performance_eficiencia",
        prompt_principal="Teste principal",
        model_name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    mock_carregar_prompt.assert_called_once_with("relatorio_performance_eficiencia")
    assert result['reposta_final'] == "Resposta"
    assert result['tokens_entrada'] == 10
    assert result['tokens_saida'] == 20

@patch('tools.requisicao_openai.OpenAILLMProvider.carregar_prompt')
@patch('tools.prompt_utils.carregar_prompt')
def test_model_name_provider_selection(mock_bedrock_prompt, mock_openai_prompt):
    mock_openai_prompt.return_value = "PROMPT OPENAI"
    mock_bedrock_prompt.return_value = "PROMPT BEDROCK"
    openai_provider = OpenAILLMProvider(secret_manager=MagicMock(), user_email="lucio.rosa@peers.com", group_resolver=MagicMock())
    bedrock_provider = AmazonBedrockProvider(secret_manager=MagicMock(), user_email="lucio.rosa@peers.com", group_resolver=MagicMock())
    # Mock boto3 client
    bedrock_provider.bedrock_runtime = MagicMock()
    bedrock_provider.bedrock_runtime.invoke_model.return_value = {
        'body': MagicMock(read=lambda: b'{"content": [{"text": "Resposta Bedrock"}], "usage": {"input_tokens": 5, "output_tokens": 15}}')
    }
    # OpenAI
    result_openai = openai_provider.executar_prompt(
        tipo_tarefa="aplicacao_de_mudancas",
        prompt_principal="Prompt OpenAI",
        model_name="gpt-4.1"
    )
    mock_openai_prompt.assert_called_with("aplicacao_de_mudancas")
    # Bedrock
    result_bedrock = bedrock_provider.executar_prompt(
        tipo_tarefa="relatorio_performance_eficiencia",
        prompt_principal="Prompt Bedrock",
        model_name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    mock_bedrock_prompt.assert_called_with("relatorio_performance_eficiencia")
    assert result_bedrock['reposta_final'] == "Resposta Bedrock"
    assert result_bedrock['tokens_entrada'] == 5
    assert result_bedrock['tokens_saida'] == 15

@patch('tools.prompt_utils.carregar_prompt')
def test_prompt_file_loading(mock_carregar_prompt):
    mock_carregar_prompt.return_value = "Conteudo do prompt"
    result = carregar_prompt("relatorio_performance_eficiencia")
    mock_carregar_prompt.assert_called_once_with("relatorio_performance_eficiencia")
