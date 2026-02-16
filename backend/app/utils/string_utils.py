import unicodedata
import re

def normalize_string_general(text: str) -> str:
    """
    Normalização robusta: 
    1. Remove acentos (Café -> Cafe)
    2. Transforma em minúsculo
    3. Remove caracteres especiais (mantém apenas letras, números e underscores)
    4. Substitui múltiplos espaços/hífens por um único underscore
    """
    if not text:
        return ""
    
    # Remove acentos e normaliza para formato Unicode de decomposição
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # Converte para minúsculo e remove caracteres que não são letras/números
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Substitui espaços e hífens por underscore
    text = re.sub(r'[\s-]+', '_', text)
    
    return text
