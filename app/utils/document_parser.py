import io
import docx
import logging
from fastapi import UploadFile

logger = logging.getLogger("mcp_prototype.utils")

async def extract_text_from_docx(file: UploadFile) -> str:
    """Extrai texto de um arquivo .docx físico recebido no endpoint."""
    if not file:
        return ""
    try:
        content = await file.read()
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        logger.error(f"Erro ao extrair texto do DOCX ({file.filename}): {e}")
        return ""
