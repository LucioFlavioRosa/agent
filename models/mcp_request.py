from pydantic import BaseModel
from typing import Optional

class MCPRequest(BaseModel):
    project_id: str
    analysis_type: str
    instrucoes_extras: Optional[str] = None
    arquivo_docx: Optional[str] = None
    nome_projeto: Optional[str] = None
    usuario_executor: Optional[str] = None
