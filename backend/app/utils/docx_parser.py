import io
from docx import Document

def extrair_texto_docx_em_memoria(file_bytes: bytes) -> str:
    """
    Recebe os bytes de um arquivo .docx e retorna todo o texto contido nele.
    Tudo feito em memória RAM (muito rápido e seguro).
    """
    # 1. Converte os bytes puros em um fluxo de arquivo legível (File-like object)
    file_stream = io.BytesIO(file_bytes)
    
    # 2. Abre o fluxo usando a biblioteca docx
    documento = Document(file_stream)
    
    # 3. Extrai e junta o texto de todos os parágrafos
    texto_completo = "\n".join([paragrafo.text for paragrafo in documento.paragraphs])
    
    return texto_completo
