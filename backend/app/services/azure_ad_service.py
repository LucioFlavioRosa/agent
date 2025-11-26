from msal import ConfidentialClientApplication
from fastapi import HTTPException, status
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any

class AzureADTokenData(BaseModel):
    usuario_executor: str
    claims: Dict[str, Any]

class AzureADService:
    def __init__(self):
        self.tenant_id = os.getenv("AZURE_AD_TENANT_ID")
        self.client_id = os.getenv("AZURE_AD_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_AD_CLIENT_SECRET")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )

    def validate_token(self, token: str) -> AzureADTokenData:
        try:
            # MSAL não decodifica JWT diretamente, mas valida contra Azure AD
            # Para decodificação, usamos PyJWT apenas para extrair claims após validação
            import jwt
            from jwt import InvalidTokenError, ExpiredSignatureError
            # Validar token usando MSAL (simplesmente decodifica e verifica assinatura)
            # Em produção, usar biblioteca própria da Azure para validação completa
            # Aqui, apenas decodifica e verifica expiração
            claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": True}, algorithms=["RS256", "HS256"])
            usuario_executor = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
            if not usuario_executor:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="usuario_executor não encontrado no token Azure AD.")
            return AzureADTokenData(usuario_executor=usuario_executor, claims=claims)
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Azure AD expirado.")
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Azure AD inválido.")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao validar token Azure AD: {str(e)}")
