from fastapi import HTTPException, status, Request
from jose import jwt, JWTError
from pydantic import BaseModel
import os
from typing import Any, Dict

# Classe para representar os dados extraídos do token
class TokenData(BaseModel):
    usuario_executor: str
    exp: int
    sub: str = None
    # Adicione outros claims relevantes conforme necessário

# Carrega a chave secreta do ambiente
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def validate_jwt_token(token: str) -> TokenData:
    """
    Decodifica e valida o token JWT. Retorna os claims como TokenData.
    Lança HTTPException(401) se inválido.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        usuario_executor = payload.get("usuario_executor")
        if not usuario_executor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="usuario_executor não encontrado no token")
        exp = payload.get("exp")
        sub = payload.get("sub")
        return TokenData(usuario_executor=usuario_executor, exp=exp, sub=sub)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT inválido ou expirado")
