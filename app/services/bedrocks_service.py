import logging

logger = logging.getLogger("mcp_prototype.llm")

async def generate_html_prototype(mega_prompt: str) -> str:
    """
    Integração com LLM (OpenAI, Anthropic, etc).
    """
    logger.info("🧠 Enviando Mega Prompt para a IA...")
    
    # Exemplo Mock (Substitua pela sua lib da OpenAI/Azure)
    html_mock = f"<!DOCTYPE html>\n<html lang='pt-br'>\n<head><title>Protótipo Gerado</title></head>\n<body><h1>Protótipo Gerado com Sucesso</h1></body>\n</html>"
    return html_mock
