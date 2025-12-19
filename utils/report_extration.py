import re
import json

def extrair_conteudo_json(dados):
    """
    1. Varre recursivamente o dicionário/lista buscando uma string que contenha ```json
    2. Extrai o conteúdo dentro do bloco de código
    3. Retorna o objeto JSON (dict) pronto
    """
    
    # Função interna para encontrar a string crua (o texto do LLM)
    def encontrar_string_com_markdown(obj):
        if isinstance(obj, str):
            if "```json" in obj:
                return obj
        elif isinstance(obj, dict):
            for value in obj.values():
                resultado = encontrar_string_com_markdown(value)
                if resultado: return resultado
        elif isinstance(obj, list):
            for item in obj:
                resultado = encontrar_string_com_markdown(item)
                if resultado: return resultado
        return None

    # 1. Acha a string que tem o markdown
    texto_bruto = encontrar_string_com_markdown(dados)
    
    if not texto_bruto:
        # Se não achou markdown, tenta ver se o próprio input já é o dict alvo
        # ou retorna erro/vazio dependendo da sua regra de negócio
        return dados 

    # 2. Usa Regex para pegar TUDO que está entre ```json e ```
    # O re.DOTALL faz o ponto (.) pegar quebras de linha também
    match = re.search(r"```json\s*(.*?)\s*```", texto_bruto, re.DOTALL | re.IGNORECASE)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON extraído: {e}")
            return None
    
    return None
