import jwt
from fastapi import HTTPException, status
from typing import Any
from datetime import datetime, timezone
from app.models.auth_models import UserInfo, TokenPayload
from app.tools.azure_secret_manager import AzureSecretManager

SECRET_NAME = "jwt-signing-key"  # Nome do segredo no Azure Key Vault
ALGORITHM = "HS256"  # Ajuste conforme o algoritmo do JWT utilizado

def validate_jwt_token(token: str) -> UserInfo:
    """
    Valida o token JWT recebido do front-end, utilizando a chave secreta do Azure Key Vault.
    Retorna um objeto UserInfo se válido, lança HTTPException(401) se inválido.
    """
    try:
        secret_manager = AzureSecretManager()
        secret_key = secret_manager.get_secret(SECRET_NAME)
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        # Validação de expiração
        exp = payload.get("exp")
        if exp is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT sem expiração definida.")
        now = datetime.now(timezone.utc).timestamp()
        if now > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT expirado.")
        usuario_executor = payload.get("usuario_executor")
        email = payload.get("email")
        if not usuario_executor or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Campos obrigatórios ausentes no token JWT.")
        return UserInfo(usuario_executor=usuario_executor, email=email, exp=exp)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT inválido.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao validar token JWT: {str(e)}")
