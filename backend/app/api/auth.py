from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import os
from backend.app.core.config import settings
from backend.app.middleware.auth_middleware import get_current_user
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()

class AuthConfigResponse(BaseModel):
    client_id: str
    tenant_id: str
    authority: str
    redirect_uri: str
    scope: str

class AuthLoginResponse(BaseModel):
    user_info: dict
    projects: list

@router.get("/config", response_model=AuthConfigResponse, tags=["Auth"])
def get_auth_config():
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

@router.post("/login", response_model=AuthLoginResponse, tags=["Auth"])
async def auth_login(current_user: dict = Depends(get_current_user)):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    if not usuario_executor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado.")
    try:
        projects = await ProjectStateService.list_user_projects(usuario_executor)
        for p in projects:
            if isinstance(p, dict):
                p.pop("analysis_name", None)
        # Adiciona project_id em cada projeto retornado
        for idx, p in enumerate(projects):
            if isinstance(p, dict):
                if "project_id" not in p:
                    p["project_id"] = p.get("project_id")
        # Filtro para garantir que project_id esteja presente
        projects = [p for p in projects if "project_id" in p]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar projetos do usuário: {str(e)}")
    return AuthLoginResponse(user_info=current_user, projects=projects)
