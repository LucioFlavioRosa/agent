import logging
from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from backend.app.services.azure_ad_service import AzureADService

logger = logging.getLogger("AuthMiddleware")

_azure_ad_service_instance = None

def get_azure_ad_service() -> AzureADService:
    global _azure_ad_service_instance
    if _azure_ad_service_instance is None:
        logger.info("Inicializando AzureADService sob demanda (primeira requisição)...")
        try:
            _azure_ad_service_instance = AzureADService()
        except Exception as e:
            logger.critical(f"Falha crítica ao inicializar AzureADService: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro interno na configuração de autenticação."
            )
    return _azure_ad_service_instance

def get_current_user(request: Request) -> dict:
    auth: str = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente.")
    scheme, param = get_authorization_scheme_param(auth)
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de autenticação inválido. Use Bearer.")
    try:
        service = get_azure_ad_service()
        user = service.validate_token(param)
        if hasattr(user, "claims"):
            return user.claims
        return user
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro inesperado na validação do token: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro inesperado na validação do token.")

def _extract_usuario_executor(current_user: dict) -> str:
    return current_user.get("usuario_executor") or current_user.get("sub")
