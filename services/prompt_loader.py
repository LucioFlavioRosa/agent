import os
import logging

# Configura logger
logger = logging.getLogger("PromptLoaderService")

def load_prompt_instructions(prompt_filename: str) -> str:
    # 1. Pega o diretório onde este arquivo (prompt_loader.py) está: .../services
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Sobe um nível para a raiz do projeto: .../
    project_root = os.path.dirname(current_dir)
    
    # 3. Caminho esperado da pasta de prompts: .../tools/prompts
    prompts_dir = os.path.join(project_root, 'tools', 'prompts')
    
    # 4. Caminho final do arquivo
    prompt_path = os.path.join(prompts_dir, prompt_filename)

    logger.info(f"🔍 [DEBUG] Tentando ler prompt em: {prompt_path}")

    if not os.path.isfile(prompt_path):
        # --- BLOCÃO DE DIAGNÓSTICO ---
        logger.error(f"❌ ARQUIVO NÃO ENCONTRADO: {prompt_path}")
        
        # Verifica se a pasta 'tools' existe
        tools_dir = os.path.join(project_root, 'tools')
        if not os.path.exists(tools_dir):
             logger.error(f"😱 A pasta 'tools' NEM EXISTE na raiz: {project_root}")
             # Lista a raiz para ver o que subiu
             try:
                 logger.error(f"📂 Conteúdo da Raiz: {os.listdir(project_root)}")
             except: pass
        
        # Verifica se a pasta 'prompts' existe
        elif not os.path.exists(prompts_dir):
             logger.error(f"😱 A pasta 'tools' existe, mas 'prompts' NÃO: {tools_dir}")
             try:
                 logger.error(f"📂 Conteúdo de tools: {os.listdir(tools_dir)}")
             except: pass
             
        # A pasta existe, mas o arquivo não
        else:
             logger.error(f"🤔 A pasta 'prompts' existe. Listando arquivos nela:")
             try:
                 arquivos = os.listdir(prompts_dir)
                 logger.error(f"📄 Arquivos disponíveis: {arquivos}")
             except Exception as e:
                 logger.error(f"Erro ao listar: {e}")

        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_path}")

    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
