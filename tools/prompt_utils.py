import os

def carregar_prompt(tipo_tarefa: str) -> str:
    caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_tarefa}.md')
    if not os.path.isfile(caminho_prompt):
        raise FileNotFoundError(f"Arquivo de prompt para '{tipo_tarefa}' não encontrado: {caminho_prompt}")
    try:
        with open(caminho_prompt, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            if not conteudo or len(conteudo.strip()) == 0:
                raise ValueError(f"Prompt para '{tipo_tarefa}' está vazio: {caminho_prompt}")
            return conteudo
    except Exception as e:
        raise RuntimeError(f"Erro ao ler o arquivo de prompt '{caminho_prompt}': {e}")
