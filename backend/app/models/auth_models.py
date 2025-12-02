from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TokenData(BaseModel):
    usuario_executor: str = Field(..., description="Identificador do usuário extraído do JWT.")
    exp: Optional[int] = Field(None, description="Timestamp de expiração do token.")
    sub: Optional[str] = Field(None, description="Subject do token.")
    iss: Optional[str] = Field(None, description="Issuer do token.")
    aud: Optional[str] = Field(None, description="Audience do token.")
    additional_claims: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Outros claims presentes no JWT.")
