import os

def carregar_prompt(tipo_tarefa: str) -> str:
    caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_tarefa}.md')
    with open(caminho_prompt, 'r', encoding='utf-8') as f:
        return f.read()
