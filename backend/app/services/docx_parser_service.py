from fastapi import UploadFile, HTTPException
from docx import Document
import io
from typing import Optional

async def extract_text_from_docx(file: UploadFile, user_comment: Optional[str] = None) -> str:
    try:
        file.file.seek(0)
        doc_bytes = await file.read()
        doc_stream = io.BytesIO(doc_bytes)
        document = Document(doc_stream)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        texto_extraido = '\n'.join(full_text)
        if user_comment:
            texto_extraido = f"{texto_extraido}\n\n--- Comentário do Usuário ---\n{user_comment}"
        return texto_extraido
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")