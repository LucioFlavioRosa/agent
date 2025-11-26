from typing import Optional
from docx import Document
from io import BytesIO

def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extrai todo o texto de um arquivo DOCX fornecido como bytes.
    Retorna string vazia em caso de falha.
    """
    try:
        doc = Document(BytesIO(file_content))
        full_text = []
        for para in doc.paragraphs:
            if para.text:
                full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        # Logar erro se necessário
        return ""
