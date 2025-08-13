import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from tools.rag_retriever import buscar_politicas_relevantes


key_vault_url = os.environ["KEY_VAULT_URL"]
credential = DefaultAzureCredential()
client = SecretClient(vault_url=key_vault_url, credential=credential)
OPENAI_API_KEY = client.get_secret("openaiapi").value
if not OPENAI_API_KEY:
    raise ValueError("A chave da API da OpenAI não foi encontrada.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def carregar_prompt(tipo_analise: str) -> str:
    caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_analise}.md')
    try:
        with open(caminho_prompt, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Arquivo de prompt para a análise '{tipo_analise}' não encontrado em: {caminho_prompt}")


# [ALTERADO] A função agora integra a busca RAG
def executar_analise_llm(
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        model_name: str,
        max_token_out: int
) -> dict:
    
    # --- ETAPA 1: BUSCA (Retrieval) ---
    # Usa o tipo de análise como base para buscar políticas relevantes na base de conhecimento.
    politicas_relevantes = buscar_politicas_relevantes(query=f"políticas de {tipo_analise} para desenvolvimento de software")
    
    # --- ETAPA 2: AUMENTAÇÃO (Augmentation) ---
    prompt_sistema_base = carregar_prompt(tipo_analise)
    
    # Adiciona as políticas recuperadas e a nova instrução ao prompt do sistema
    prompt_sistema_aumentado = (
        f"{prompt_sistema_base}\n\n"
        "--- POLÍTICAS RELEVANTES DA EMPRESA ---\n"
        "Você DEVE, obrigatoriamente, basear sua análise e sugestões nas políticas da empresa descritas abaixo. "
        "Para cada sugestão de mudança que você fizer, adicione uma chave 'politica_referenciada' "
        "indicando a 'Fonte' e 'Seção' da política que justifica a mudança.\n\n"
        f"{politicas_relevantes}"
    )

    mensagens = [
        {"role": "system", "content": prompt_sistema_aumentado},
        {'role': 'user', 'content': codigo},
        {'role': 'user',
         'content': f'Instruções extras do usuário: {analise_extra}' if analise_extra.strip() else 'Nenhuma instrução extra.'}
    ]

    # --- ETAPA 3: GERAÇÃO (Generation) ---
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=mensagens,
            temperature=0.3, # Reduz a temperatura para respostas mais factuais e baseadas nas políticas
            max_tokens=max_token_out
        )
        conteudo_resposta = response.choices[0].message.content.strip()
        return {
            'reposta_final': conteudo_resposta,
            'tokens_entrada': response.usage.prompt_tokens,
            'tokens_saida': response.usage.completion_tokens
        }

    except Exception as e:
        print(f"ERRO: Falha na chamada à API da OpenAI para análise '{tipo_analise}'. Causa: {e}")
        raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
