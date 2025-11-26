from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
import jwt
import os
from datetime import datetime, timedelta

router = APIRouter()

# Configurações (ideal: usar variáveis de ambiente seguras)
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "changeme-supersecret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60))

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Exemplo de validação simples (substitua por consulta real a banco/AD)
def authenticate_user(username: str, password: str) -> Optional[dict]:
    # Exemplo: usuário e senha fixos (NUNCA use em produção)
    if username == "admin" and password == "admin123":
        return {"sub": username, "usuario_executor": username}
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")
    access_token = create_access_token(user)
    return LoginResponse(access_token=access_token, expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
