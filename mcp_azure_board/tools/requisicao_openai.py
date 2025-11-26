import openai
import os

def executar_openai(prompt, model="gpt-4", max_tokens=2048, temperature=0.7, api_key=None):
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key do OpenAI não fornecida.")
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response['choices'][0]['message']['content']
