import pytest
from fastapi import HTTPException
from datetime import datetime, timedelta
import jwt

# Supondo que a função validate_jwt_token e a classe TokenData estão disponíveis no backend.jwt_validator
from backend.jwt_validator import validate_jwt_token, TokenData

SECRET_KEY = "testsecret"
ALGORITHM = "HS256"


def create_token(data, secret=SECRET_KEY, algorithm=ALGORITHM, expire_delta=timedelta(minutes=5)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expire_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algorithm)

def test_validate_jwt_token_valid():
    token_data = {"sub": "user1", "email": "user1@example.com"}
    token = create_token(token_data)
    result = validate_jwt_token(token, SECRET_KEY, ALGORITHM)
    assert isinstance(result, TokenData)
    assert result.sub == "user1"
    assert result.email == "user1@example.com"

def test_validate_jwt_token_expired():
    token_data = {"sub": "user2", "email": "user2@example.com"}
    token = create_token(token_data, expire_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        validate_jwt_token(token, SECRET_KEY, ALGORITHM)
    assert exc_info.value.status_code == 401

def test_validate_jwt_token_invalid_signature():
    token_data = {"sub": "user3", "email": "user3@example.com"}
    token = create_token(token_data, secret="wrongsecret")
    with pytest.raises(HTTPException) as exc_info:
        validate_jwt_token(token, SECRET_KEY, ALGORITHM)
    assert exc_info.value.status_code == 401

def test_validate_jwt_token_malformed():
    malformed_token = "not.a.valid.token"
    with pytest.raises(HTTPException) as exc_info:
        validate_jwt_token(malformed_token, SECRET_KEY, ALGORITHM)
    assert exc_info.value.status_code == 401
