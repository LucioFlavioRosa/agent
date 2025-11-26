from fastapi import APIRouter, Header, HTTPException, status, Depends
from typing import Optional, Dict
import jwt
import os

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def validate_jwt_token(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT ausente ou inválido.")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        usuario_executor = payload.get("usuario_executor")
        email = payload.get("email")
        if not usuario_executor or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT sem campos obrigatórios.")
        return {"usuario_executor": usuario_executor, "email": email}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT inválido.")


@router.post("/auth/validate-token", tags=["Auth"])
def validate_token_route(user_info: Dict = Depends(validate_jwt_token)):
    return user_info
