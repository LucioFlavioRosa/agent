from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import os
from typing import Optional

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "changeme-supersecret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

class TokenData(dict):
    pass

def validate_jwt_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenData(payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

def get_current_user(request: Request) -> TokenData:
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    return validate_jwt_token(param)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)
        if not auth or scheme.lower() != "bearer":
            return await call_next(request)
        try:
            user = validate_jwt_token(param)
            request.state.user = user
        except HTTPException:
            return await call_next(request)
        response = await call_next(request)
        return response
