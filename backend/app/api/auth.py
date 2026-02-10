from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter()

class AuthLoginRequest(BaseModel):
    email: str
    empresa: str

class AuthLoginResponse(BaseModel):
    message: str
    email: str
    empresa: str

@router.post("/login", response_model=AuthLoginResponse, tags=["Auth"])
def auth_login(request: AuthLoginRequest = Body(...)):
    # Apenas confirma recebimento, sem validação de autenticação
    return AuthLoginResponse(
        message="Login recebido com sucesso.",
        email=request.email,
        empresa=request.empresa
    )
