from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import os
import uuid
from backend.app.core.config import settings
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.services.redis_session_service import RedisSessionService

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
    session_id: str

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
    usuario_executor = _extract_usuario_executor(current_user)
    if not usuario_executor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado.")
    projects = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
    session_id = None
    if projects:
        projeto_mais_recente = projects[0]
        projeto_nome = projeto_mais_recente.get("projeto")
        session_id = await ProjectStateService.get_session_id_from_latest_state(usuario_executor, projeto_nome)
    if not session_id:
        session_id = str(uuid.uuid4())
        redis_service = RedisSessionService()
        redis_service.create_session(
            usuario_executor=usuario_executor,
            projeto="__login__",
            analysis_type="__login__",
            comentario_usuario=None,
            extracted_text=None,
            project_id=None,
            session_id=session_id
        )
    return AuthLoginResponse(user_info=current_user, projects=projects, session_id=session_id)
