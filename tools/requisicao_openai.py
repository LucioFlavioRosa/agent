import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Obtém o URL do Key Vault das variáveis de ambiente.
# Você deve configurar KEY_VAULT_URL nas configurações do App Service.
key_vault_url = os.environ["KEY_VAULT_URL"]

# Cria um cliente para se conectar ao Key Vault.
# DefaultAzureCredential usa a identidade gerenciada do App Service automaticamente.
credential = DefaultAzureCredential()
client = SecretClient(vault_url=key_vault_url, credential=credential)

# Obtém o segredo (o token da OpenAI) do Key Vault.
# O nome do segredo deve ser o mesmo que você configurou no Key Vault.
OPENAI_API_KEY = client.get_secret("openaiapi").value

if not OPENAI_API_KEY:
    raise ValueError("A chave da API da OpenAI não foi encontrada. Verifique as configurações do Key Vault.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def carregar_prompt(tipo_analise: str) -> str:
    caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_analise}.md')
    try:
        with open(caminho_prompt, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Arquivo de prompt para a análise '{tipo_analise}' não encontrado em: {caminho_prompt}")


def executar_analise_llm(
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        model_name: str,
        max_token_out: int
) -> dict:
    prompt_sistema = carregar_prompt(tipo_analise)

    mensagens = [
        {"role": "system", "content": prompt_sistema},
        {'role': 'user', 'content': codigo},
        {'role': 'user',
         'content': f'Instruções extras do usuário a serem consideradas na análise: {analise_extra}' if analise_extra.strip() else 'Nenhuma instrução extra fornecida pelo usuário.'}
    ]

    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=mensagens,
            temperature=0.5,
            max_tokens=max_token_out
        )
        conteudo_resposta = response.choices[0].message.content.strip()
        return {'reposta_final': conteudo_resposta,
                'tokens_entrada': response.usage.prompt_tokens,
                'tokens_saida': response.usage.completion_tokens}

    except Exception as e:
        print(f"ERRO: Falha na chamada à API da OpenAI para análise '{tipo_analise}'. Causa: {e}")
        raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
