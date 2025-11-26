from fastapi import UploadFile, HTTPException
from docx import Document
import io

async def extract_text_from_docx(file: UploadFile) -> str:
    """
    Extrai todo o texto de um arquivo .docx recebido via UploadFile.
    """
    try:
        file.file.seek(0)
        doc_bytes = await file.read()
        doc_stream = io.BytesIO(doc_bytes)
        document = Document(doc_stream)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
