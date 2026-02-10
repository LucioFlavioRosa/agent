from fastapi import APIRouter
from backend.app.models.user_models import UserContext
from pydantic import BaseModel

router = APIRouter()

class AuthLoginResponse(BaseModel):
    message: str
    email: str
    empresa: str

@router.post("/login", response_model=AuthLoginResponse, tags=["Auth"])
def auth_login(user: UserContext):
    # Não faz nenhuma validação de autenticação, apenas confirma recebimento
    return AuthLoginResponse(
        message="Login recebido com sucesso.",
        email=user.email,
        empresa=user.empresa
    )
