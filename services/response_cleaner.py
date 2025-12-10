import json
import re

def clean_llm_response(raw_response):
    try:
        resultado = raw_response.get('resultado', {}).get('reposta_final', '')
        if isinstance(resultado, dict):
            resultado = resultado.get('reposta_final', '')
        cleaned = resultado.replace('', '').replace('', '').strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        json.loads(cleaned)
        return cleaned
    except Exception:
        return ''
