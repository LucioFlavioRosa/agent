from fastapi import APIRouter
from pydantic import BaseModel
import os
from backend.app.core.config import settings

router = APIRouter()

class AuthConfigResponse(BaseModel):
    client_id: str
    tenant_id: str
    authority: str
    redirect_uri: str
    scope: str

@router.get("/config", response_model=AuthConfigResponse, tags=["Auth"])
def get_auth_config():
    """
    Endpoint público para o frontend obter as configurações necessárias para MSAL.js.
    Não expõe segredos, apenas dados públicos de configuração.
    """
    client_id = os.environ.get("AZURE_AD_CLIENT_ID", getattr(settings, "AZURE_AD_CLIENT_ID", ""))
    tenant_id = os.environ.get("AZURE_AD_TENANT_ID", getattr(settings, "AZURE_AD_TENANT_ID", ""))
    redirect_uri = os.environ.get("AZURE_AD_REDIRECT_URI", getattr(settings, "AZURE_AD_REDIRECT_URI", "http://localhost:3000/auth/callback"))
    scope = os.environ.get("AZURE_SCOPE", "User.Read")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return AuthConfigResponse(
        client_id=client_id,
        tenant_id=tenant_id,
        authority=authority,
        redirect_uri=redirect_uri,
        scope=scope
    )

# O endpoint POST /auth/login foi removido por segurança.
# O fluxo recomendado agora é: o frontend obtém o token diretamente da Microsoft (MSAL.js) e envia o Bearer token para o backend.
