from pydantic import BaseModel, Field
from typing import Optional, List

class AzureADTokenData(BaseModel):
    oid: str = Field(..., description="Object ID do usuário no Azure AD.")
    preferred_username: Optional[str] = Field(None, description="Nome de usuário preferencial do Azure AD.")
    email: Optional[str] = Field(None, description="Email do usuário.")
    roles: Optional[List[str]] = Field(default_factory=list, description="Lista de roles do usuário.")
    name: Optional[str] = Field(None, description="Nome completo do usuário.")
    exp: Optional[int] = Field(None, description="Timestamp de expiração do token.")
    iss: Optional[str] = Field(None, description="Issuer do token.")
    aud: Optional[str] = Field(None, description="Audience do token.")
    sub: Optional[str] = Field(None, description="Subject do token.")
