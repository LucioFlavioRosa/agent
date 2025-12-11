import json
import re
import logging # 1. Importar o módulo de logging

# 2. Configurar o logger local para este arquivo
logger = logging.getLogger("ResponseCleaner")

def clean_llm_response(raw_response):
    try:
        cleaned = raw_response.replace('```json', '').replace('```', '').replace('\n', '').replace('\', '').strip()

        # Validação do JSON
        json.loads(cleaned)
        
        return cleaned
    
    except Exception as e:
        # É uma boa prática logar o erro aqui também para saber por que falhou
        logger.error(f"❌ Erro ao limpar resposta: {e}")
        return ''
