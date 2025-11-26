import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from datetime import datetime, timedelta
import jwt

# Supondo que validate_jwt_token está em backend.auth.jwt_validator
from backend.auth.jwt_validator import validate_jwt_token, UserInfo

SECRET = 'test_secret'
ALGORITHM = 'HS256'

@pytest.fixture
def valid_token():
    payload = {
        'sub': 'user123',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'name': 'Test User',
        'email': 'test@example.com'
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

@pytest.fixture
def expired_token():
    payload = {
        'sub': 'user123',
        'exp': datetime.utcnow() - timedelta(hours=1),
        'name': 'Test User',
        'email': 'test@example.com'
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

@pytest.fixture
def malformed_token():
    return 'malformed.token.string'

@pytest.fixture
def invalid_signature_token(valid_token):
    # Alterar um caractere do token válido para invalidar a assinatura
    return valid_token[:-1] + ('a' if valid_token[-1] != 'a' else 'b')

@patch('backend.auth.jwt_validator.AzureSecretManager')
def test_valid_token_success(mock_secret_manager, valid_token):
    instance = mock_secret_manager.return_value
    instance.get_jwt_secret.return_value = SECRET
    user_info = validate_jwt_token(valid_token)
    assert isinstance(user_info, UserInfo)
    assert user_info.user_id == 'user123'
    assert user_info.name == 'Test User'
    assert user_info.email == 'test@example.com'

@patch('backend.auth.jwt_validator.AzureSecretManager')
def test_expired_token_raises_401(mock_secret_manager, expired_token):
    instance = mock_secret_manager.return_value
    instance.get_jwt_secret.return_value = SECRET
    with pytest.raises(HTTPException) as exc:
        validate_jwt_token(expired_token)
    assert exc.value.status_code == 401
    assert 'expired' in str(exc.value.detail).lower()

@patch('backend.auth.jwt_validator.AzureSecretManager')
def test_invalid_signature_raises_401(mock_secret_manager, invalid_signature_token):
    instance = mock_secret_manager.return_value
    instance.get_jwt_secret.return_value = SECRET
    with pytest.raises(HTTPException) as exc:
        validate_jwt_token(invalid_signature_token)
    assert exc.value.status_code == 401
    assert 'signature' in str(exc.value.detail).lower() or 'invalid' in str(exc.value.detail).lower()

@patch('backend.auth.jwt_validator.AzureSecretManager')
def test_malformed_token_raises_401(mock_secret_manager, malformed_token):
    instance = mock_secret_manager.return_value
    instance.get_jwt_secret.return_value = SECRET
    with pytest.raises(HTTPException) as exc:
        validate_jwt_token(malformed_token)
    assert exc.value.status_code == 401
    assert 'malformed' in str(exc.value.detail).lower() or 'invalid' in str(exc.value.detail).lower()
