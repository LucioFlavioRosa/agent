import os

def load_prompt_instructions(prompt_filename: str) -> str:
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'tools', 'prompts')
    prompt_path = os.path.join(base_dir, prompt_filename)
    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_path}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
