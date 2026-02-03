from pydantic import BaseModel
from typing import Optional

class UserGroupMapping(BaseModel):
    usuario: str  # Email completo do usuário (ex: joao.silva@exemplo.com)
    empresa: str
    grupo: str
    descricao: Optional[str] = None  # Campo opcional para descrição
