import json
import re
import logging

logger = logging.getLogger("ResponseCleaner")

def clean_llm_response(raw_response):
    """
    Limpa a resposta da LLM removendo blocos de código Markdown (```json)
    e convertendo para um Dicionário Python.
    """
    
    # 1. Se já for um dicionário, retorna imediatamente.
    if isinstance(raw_response, dict):
        return raw_response
    
    # Garante que é string para manipulação
    if not isinstance(raw_response, str):
        raw_response = str(raw_response)

    try:
        # Log curto para debug
        logger.info(f"🧹 [CLEANER] Processando entrada (len={len(raw_response)})")

        # 2. EXTRAÇÃO DO JSON (Markdown Removal)
        match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_response, re.IGNORECASE)
        
        if match:
            # Cenário Ideal: Encontrou o bloco de código
            json_str = match.group(1).strip()
        else:
            # Cenário Fallback: Não tem bloco, tenta limpar as crases se existirem soltas
            json_str = raw_response.replace('```json', '').replace('```', '').strip()

        # 3. PARSE FINAL (String -> Dict)
        result_dict = json.loads(json_str)
        
        return result_dict

    except json.JSONDecodeError as je:
        logger.error(f"❌ [JSON ERROR] Falha ao parsear JSON. Erro: {je}")
        # Retorna um dict de erro contendo o texto cru para análise
        return {
            "error": "Falha no Parse JSON", 
            "details": str(je),
            "raw_content": raw_response[:500] # Corta para não lotar o log
        }
        
    except Exception as e:
        logger.error(f"❌ [CRITICAL ERROR] Erro desconhecido no cleaner: {e}")
        return {"error": str(e)}
