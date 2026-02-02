import os

def carregar_prompt(tipo_tarefa: str) -> str:
    caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_tarefa}.md')
    try:
        with open(caminho_prompt, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Arquivo de prompt para '{tipo_tarefa}' não encontrado: {caminho_prompt}")
