from fastapi import Request, HTTPException, status, Depends
from fastapi.security.utils import get_authorization_scheme_param
from app.services.azure_ad_service import AzureADService, AzureADTokenData

azure_ad_service = AzureADService()

class TokenData(AzureADTokenData):
    pass

def get_current_user(request: Request) -> AzureADTokenData:
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    return azure_ad_service.validate_token(param)
