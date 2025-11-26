from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class TokenPayload(BaseModel):
    usuario_executor: str = Field(..., description="Identificador único do usuário executor, extraído do JWT.")
    email: EmailStr = Field(..., description="E-mail do usuário autenticado.")
    exp: int = Field(..., description="Timestamp de expiração do token JWT.")

class UserInfo(BaseModel):
    usuario_executor: str = Field(..., description="Identificador único do usuário executor.")
    email: EmailStr = Field(..., description="E-mail do usuário autenticado.")
    exp: int = Field(..., description="Timestamp de expiração do token JWT.")
