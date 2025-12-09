from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import os
from backend.app.core.config import settings
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.services.redis_session_service import RedisSessionService
import logging

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
    logger = logging.getLogger("auth_api")
    usuario_executor = _extract_usuario_executor(current_user)
    if not usuario_executor:
        logger.error("Usuário não autenticado: usuario_executor ausente no token.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado.")
    projetos = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
    redis_service = RedisSessionService()
    resumo_list = []
    for p in projetos:
        project_id = p.get("project_id")
        resumo_state = redis_service.get_resumo_state(project_id)
        if resumo_state:
            resumo = {
                "nome_projeto": resumo_state.get("nome_projeto", ""),
                "ultima_analysis_type": resumo_state.get("ultima_analysis_type", ""),
                "created_at": resumo_state.get("created_at", None),
                "ultima_atualizacao": resumo_state.get("ultima_atualizacao", resumo_state.get("last_saved_to_blob", None)),
                "project_id": resumo_state.get("project_id")
            }
            resumo_list.append(resumo)
        else:
            resumo_list.append(p)
    logger.info(f"Login bem-sucedido para usuario_executor={usuario_executor}. Projetos retornados: {len(resumo_list)}")
    return AuthLoginResponse(user_info=current_user, projects=resumo_list)
