import pytest
from unittest.mock import MagicMock, patch
from tools.requisicao_claude import AmazonBedrockProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

class DummySecretManager:
    def __init__(self, secrets):
        self.secrets = secrets
    def get_secret(self, name):
        return self.secrets[name]

@pytest.fixture
def dummy_secrets():
    return {
        'AWS-ACCESS-KEY-ID': 'test-access-key',
        'AWS-SECRET-ACCESS-KEY': 'test-secret-key',
        'AWS-REGION': 'us-east-1'
    }

@pytest.fixture
def dummy_secret_manager(dummy_secrets):
    return DummySecretManager(dummy_secrets)

@pytest.fixture
def dummy_bedrock_client():
    client = MagicMock()
    # Simula resposta do invoke_model
    response_body = {
        'content': [{'text': 'Resposta simulada'}],
        'usage': {'input_tokens': 123, 'output_tokens': 456}
    }
    mock_response = {'body': MagicMock(read=MagicMock(return_value=json.dumps(response_body).encode('utf-8')))}
    client.invoke_model.return_value = mock_response
    return client

@patch('tools.requisicao_claude.boto3.client')
def test_init_bedrock_provider(mock_boto_client, dummy_secret_manager, dummy_bedrock_client):
    mock_boto_client.return_value = dummy_bedrock_client
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    assert provider.aws_access_key_id == 'test-access-key'
    assert provider.aws_secret_access_key == 'test-secret-key'
    assert provider.aws_region == 'us-east-1'
    assert provider.bedrock_runtime == dummy_bedrock_client

@patch('tools.requisicao_claude.boto3.client')
def test_executar_prompt_success(mock_boto_client, dummy_secret_manager, dummy_bedrock_client):
    mock_boto_client.return_value = dummy_bedrock_client
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    result = provider.executar_prompt(
        tipo_tarefa='test_task',
        prompt_principal='Prompt principal',
        instrucoes_extras='Instruções extras',
        model_name='us.test.model',
        max_token_out=1000,
        job_id='job-123'
    )
    assert result['resposta_final'] == 'Resposta simulada'
    assert result['tokens_entrada'] == 123
    assert result['tokens_saida'] == 456
    assert result['job_id'] == 'job-123'
    assert result['model_id'] == 'us.test.model'

@patch('tools.requisicao_claude.boto3.client')
def test_executar_prompt_payload_construction(mock_boto_client, dummy_secret_manager, dummy_bedrock_client):
    mock_boto_client.return_value = dummy_bedrock_client
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    with patch.object(provider.bedrock_runtime, 'invoke_model', wraps=provider.bedrock_runtime.invoke_model) as mock_invoke:
        provider.executar_prompt(
            tipo_tarefa='test_task',
            prompt_principal='Prompt principal',
            instrucoes_extras='Extra',
            model_name=None,
            max_token_out=500,
            job_id=None
        )
        args, kwargs = mock_invoke.call_args
        body = json.loads(kwargs['body'])
        assert body['max_tokens'] == 500
        assert body['temperature'] == 0.2
        assert body['messages'][0]['role'] == 'user'
        assert 'Extra' in body['messages'][0]['content'][0]['text']

@patch('tools.requisicao_claude.boto3.client')
def test_executar_prompt_error_handling(mock_boto_client, dummy_secret_manager):
    class FailingBedrockClient:
        def invoke_model(self, *args, **kwargs):
            raise Exception('Bedrock error')
    mock_boto_client.return_value = FailingBedrockClient()
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    with pytest.raises(Exception) as excinfo:
        provider.executar_prompt(
            tipo_tarefa='test_task',
            prompt_principal='Prompt principal',
            instrucoes_extras='',
            model_name=None,
            max_token_out=1000,
            job_id=None
        )
    assert 'Bedrock error' in str(excinfo.value)

@patch('tools.requisicao_claude.boto3.client')
def test_executar_prompt_com_modelo_and_rag(mock_boto_client, dummy_secret_manager, dummy_bedrock_client):
    mock_boto_client.return_value = dummy_bedrock_client
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    # Wrapper com modelo
    result_modelo = provider.executar_prompt_com_modelo(
        tipo_tarefa='test_task',
        prompt_principal='Prompt principal',
        instrucoes_extras='Extra',
        model_name='us.test.model',
        max_token_out=1000,
        job_id='job-abc'
    )
    assert result_modelo['model_id'] == 'us.test.model'
    # Wrapper com rag
    result_rag = provider.executar_prompt_com_rag(
        tipo_tarefa='test_task',
        prompt_principal='Prompt principal',
        instrucoes_extras='Extra',
        usar_rag=True,
        max_token_out=1000,
        job_id='job-def'
    )
    assert result_rag['job_id'] == 'job-def'

@patch('tools.requisicao_claude.boto3.client')
def test_default_model_id_usage(mock_boto_client, dummy_secret_manager, dummy_bedrock_client):
    mock_boto_client.return_value = dummy_bedrock_client
    provider = AmazonBedrockProvider(secret_manager=dummy_secret_manager)
    result = provider.executar_prompt(
        tipo_tarefa='test_task',
        prompt_principal='Prompt principal',
        instrucoes_extras='',
        model_name=None,
        max_token_out=1000,
        job_id=None
    )
    assert result['model_id'] == 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
