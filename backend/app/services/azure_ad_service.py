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
            import jwt
            from jwt import InvalidTokenError, ExpiredSignatureError, DecodeError
            # Decodifica o token sem verificar a assinatura (para extração de claims)
            claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": True}, algorithms=["RS256", "HS256"])
            usuario_executor = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
            if not usuario_executor:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Claim obrigatório ausente: usuario_executor (preferred_username, email ou upn não encontrado no token)"
                )
            return AzureADTokenData(usuario_executor=usuario_executor, claims=claims)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado. Por favor, faça login novamente."
            )
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Assinatura inválida do token: {str(e)}"
            )
        except DecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token JWT malformado ou inválido: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Erro inesperado ao validar token Azure AD: {str(e)}"
            )
