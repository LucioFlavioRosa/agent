from fastapi import Request, HTTPException, status, Depends
from fastapi.security.utils import get_authorization_scheme_param
from backend.app.services.azure_ad_service import AzureADService, AzureADTokenData

azure_ad_service = AzureADService()

def get_current_user(request: Request) -> dict:
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente.")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de autenticação inválido. Use Bearer.")
    try:
        user = azure_ad_service.validate_token(param)
        if hasattr(user, "claims"):
            return user.claims
        return user
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro inesperado na validação do token: {str(exc)}")
