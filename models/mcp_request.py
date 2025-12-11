from pydantic import BaseModel
from typing import Optional

class MCPRequest(BaseModel):
    project_id: str
    analysis_type: str
    instrucoes_extras: Optional[str] = None
    nome_projeto: Optional[str] = None
    usuario_executor: Optional[str] = None
    texto_extraido_do_docx: Optional[str] = None
