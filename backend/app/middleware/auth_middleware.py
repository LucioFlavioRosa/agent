from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from backend.app.services.azure_ad_service import AzureADService, AzureADTokenData

azure_ad_service = AzureADService()

class TokenData(AzureADTokenData):
    pass

def get_current_user(request: Request) -> AzureADTokenData:
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    # Validação segura do token JWT usando assinatura e chaves públicas (PyJWKClient, RS256)
    return azure_ad_service.validate_token(param)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)
        if not auth or scheme.lower() != "bearer":
            return await call_next(request)
        try:
            # Validação segura do token JWT usando assinatura e chaves públicas (PyJWKClient, RS256)
            user = azure_ad_service.validate_token(param)
            request.state.user = user
        except HTTPException:
            return await call_next(request)
        response = await call_next(request)
        return response
