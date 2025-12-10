import json
import re
import logging # 1. Importar o módulo de logging

# 2. Configurar o logger local para este arquivo
logger = logging.getLogger("ResponseCleaner")

def clean_llm_response(raw_response):
    try:
        resultado = raw_response.get('resultado', {}).get('reposta_final', '')
        
        if isinstance(resultado, dict):
            resultado = resultado.get('reposta_final', '')
            
        # 3. Imprimir a variável no log (Isso aparecerá no Log Stream do Azure)
        logger.info(f"🔍 [RAW LLM OUTPUT]: {resultado}")

        # Lógica original de limpeza
        # Nota: Ajustei o replace abaixo pois no seu snippet estava replace('', ''), 
        # assumindo que você queria remover blocos de código markdown.
        cleaned = resultado.replace('```json', '').replace('```', '').strip()
        
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
            
        # Validação do JSON
        json.loads(cleaned)
        
        return cleaned
    except Exception as e:
        # É uma boa prática logar o erro aqui também para saber por que falhou
        logger.error(f"❌ Erro ao limpar resposta: {e}")
        return ''
