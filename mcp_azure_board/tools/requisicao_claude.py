import os
import requests

def executar_claude(prompt, model="claude-2", max_tokens=2048, temperature=0.7, api_key=None):
    api_key = api_key or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("API key do Claude não fornecida.")
    url = "https://api.anthropic.com/v1/complete"
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens_to_sample": max_tokens,
        "temperature": temperature
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json().get("completion", "")
