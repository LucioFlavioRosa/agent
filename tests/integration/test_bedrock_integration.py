import os
import pytest
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.requisicao_claude import AmazonBedrockProvider

@pytest.fixture(scope="module")
def bedrock_provider():
    secret_manager = AzureSecretManager(vault_type=VaultType.LLM)
    return AmazonBedrockProvider(secret_manager=secret_manager)

def test_invoke_real_model_success(bedrock_provider):
    tipo_tarefa = "relatorio_implentacao_feature"
    prompt_principal = "Explique o propósito deste código."
    model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    result = bedrock_provider.executar_prompt(
        tipo_tarefa=tipo_tarefa,
        prompt_principal=prompt_principal,
        model_name=model_id
    )
    assert isinstance(result['resposta_final'], str)
    assert len(result['resposta_final']) > 0
    assert isinstance(result['tokens_entrada'], int)
    assert isinstance(result['tokens_saida'], int)

def test_fallback_to_default_model(bedrock_provider):
    tipo_tarefa = "relatorio_implentacao_feature"
    prompt_principal = "Teste de fallback para modelo padrão."
    result = bedrock_provider.executar_prompt(
        tipo_tarefa=tipo_tarefa,
        prompt_principal=prompt_principal,
        model_name=None
    )
    assert result['model_id'] == "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert isinstance(result['resposta_final'], str)
    assert len(result['resposta_final']) > 0

def test_instrucoes_extras_concatenation(bedrock_provider):
    tipo_tarefa = "relatorio_implentacao_feature"
    prompt_principal = "Prompt principal."
    instrucoes_extras = "Estas são instruções extras para o Bedrock."
    result = bedrock_provider.executar_prompt(
        tipo_tarefa=tipo_tarefa,
        prompt_principal=prompt_principal,
        instrucoes_extras=instrucoes_extras
    )
    assert "instruções extras".lower() in result['resposta_final'].lower() or instrucoes_extras.lower() in result['resposta_final'].lower()

def test_response_structure(bedrock_provider):
    tipo_tarefa = "relatorio_implentacao_feature"
    prompt_principal = "Teste de estrutura da resposta."
    result = bedrock_provider.executar_prompt(
        tipo_tarefa=tipo_tarefa,
        prompt_principal=prompt_principal
    )
    assert set(result.keys()) >= {"resposta_final", "tokens_entrada", "tokens_saida", "job_id", "model_id"}
