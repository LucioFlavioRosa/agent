import os
import logging

# Configura o logger para imprimir no console do Azure
logger = logging.getLogger("PromptUtils")

def carregar_prompt(tipo_tarefa: str) -> str:
    # 1. Pega o diretório onde este arquivo (prompt_utils.py) está
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Monta o caminho para a pasta prompts
    dir_prompts = os.path.join(base_dir, 'prompts')
    
    # 3. Monta o caminho final do arquivo
    # Garante que o nome do arquivo tenha .md
    nome_arquivo = f'{tipo_tarefa}.md' if not tipo_tarefa.endswith('.md') else tipo_tarefa
    caminho_prompt = os.path.join(dir_prompts, nome_arquivo)

    logger.info(f"📂 Tentando carregar prompt: {caminho_prompt}")

    try:
        with open(caminho_prompt, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # --- DIAGNÓSTICO DE ERRO ---
        # Se falhar, vamos listar o que existe na pasta para entender o porquê
        msg_erro = f"Arquivo de prompt não encontrado: {caminho_prompt}"
        
        if os.path.exists(dir_prompts):
            arquivos = os.listdir(dir_prompts)
            logger.error(f"❌ A pasta '{dir_prompts}' existe, mas o arquivo '{nome_arquivo}' não.")
            logger.error(f"📄 Arquivos disponíveis nesta pasta: {arquivos}")
        else:
            logger.error(f"❌ A pasta de prompts NÃO EXISTE no servidor: {dir_prompts}")
            logger.error("Dica: Verifique se a pasta 'prompts' foi incluída no deploy e não está no .gitignore ou .dockerignore")
            
            # Tenta listar a pasta pai (tools) para ver o que tem lá
            try:
                logger.error(f"Conteúdo da pasta 'tools': {os.listdir(base_dir)}")
            except:
                pass

        raise FileNotFoundError(msg_erro)
