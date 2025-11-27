import requests
from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from jose import jwt, JWTError, ExpiredSignatureError
from jose.utils import base64url_decode
from backend.app.core.config import settings
import time
import threading

class AzureADTokenData(BaseModel):
    usuario_executor: str
    claims: Dict[str, Any]

class JWKSCache:
    """
    Cache simples para JWKS (chaves públicas do Azure AD).
    """
    _lock = threading.Lock()
    _jwks = None
    _last_fetch = 0
    _cache_ttl = 60 * 60  # 1 hora

    @classmethod
    def get_jwks(cls, jwks_uri: str):
        now = time.time()
        with cls._lock:
            if cls._jwks is None or (now - cls._last_fetch) > cls._cache_ttl:
                resp = requests.get(jwks_uri, timeout=10)
                resp.raise_for_status()
                cls._jwks = resp.json()
                cls._last_fetch = now
        return cls._jwks

    @classmethod
    def get_key(cls, kid: str, jwks_uri: str):
        jwks = cls.get_jwks(jwks_uri)
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                return key
        return None

class AzureADService:
    def __init__(self):
        self.jwks_uri = settings.AZURE_AD_JWKS_URI
        self.issuer = settings.AZURE_AD_ISSUER
        self.audience = settings.AZURE_AD_AUDIENCE

    def validate_token(self, token: str) -> AzureADTokenData:
        try:
            # 1. Decodifica header do JWT para obter o 'kid'
            headers = jwt.get_unverified_header(token)
            kid = headers.get('kid')
            if not kid:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT sem 'kid' no header.")
            # 2. Busca chave pública correta do JWKS (com cache)
            key = JWKSCache.get_key(kid, self.jwks_uri)
            if not key:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave pública não encontrada para o token JWT.")
            # 3. Monta chave pública para python-jose
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            # 4. Decodifica e valida assinatura, expiração, issuer e audience
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[key.get('alg', 'RS256')],
                audience=self.audience,
                issuer=self.issuer
            )
            usuario_executor = (
                claims.get("preferred_username") or
                claims.get("email") or
                claims.get("upn")
            )
            if not usuario_executor:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="usuario_executor não encontrado no token Azure AD.")
            return AzureADTokenData(usuario_executor=usuario_executor, claims=claims)
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Azure AD expirado.")
        except JWTError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token Azure AD inválido: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao validar token Azure AD: {str(e)}")
