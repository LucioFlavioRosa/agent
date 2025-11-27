import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

# Supondo que AzureADService e AzureADTokenData estão em backend/app/services/azure_ad_service.py
from backend.app.services.azure_ad_service import AzureADService, AzureADTokenData

class DummyToken:
    def __init__(self, claims):
        self.claims = claims

@patch('backend.app.services.azure_ad_service.jwt')
def test_validate_token_valid(mock_jwt):
    claims = {
        'preferred_username': 'user1',
        'email': 'user1@example.com',
        'exp': 9999999999,
        'sub': 'user1',
        'iss': 'https://login.microsoftonline.com/',
        'aud': 'api://backend-app'
    }
    mock_jwt.decode.return_value = claims
    service = AzureADService()
    token = 'valid_token'
    result = service.validate_token(token)
    assert isinstance(result, AzureADTokenData)
    assert result.usuario_executor == 'user1'
    assert result.claims['email'] == 'user1@example.com'
    assert result.claims['exp'] == 9999999999
    assert result.claims['sub'] == 'user1'

@patch('backend.app.services.azure_ad_service.jwt')
def test_validate_token_expired(mock_jwt):
    mock_jwt.decode.side_effect = Exception('Signature has expired')
    service = AzureADService()
    token = 'expired_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'Token Azure AD expirado' in str(exc_info.value.detail)

@patch('backend.app.services.azure_ad_service.jwt')
def test_validate_token_invalid_signature(mock_jwt):
    mock_jwt.decode.side_effect = Exception('Invalid signature')
    service = AzureADService()
    token = 'invalid_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'Token Azure AD inválido' in str(exc_info.value.detail)

@patch('backend.app.services.azure_ad_service.jwt')
def test_validate_token_missing_claim(mock_jwt):
    claims = {
        'exp': 9999999999,
        'sub': 'user1'
        # missing preferred_username/email/upn
    }
    mock_jwt.decode.return_value = claims
    service = AzureADService()
    token = 'missing_claim_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'usuario_executor não encontrado' in str(exc_info.value.detail)

@patch('backend.app.services.azure_ad_service.jwt')
def test_validate_token_other_error(mock_jwt):
    mock_jwt.decode.side_effect = Exception('Some other error')
    service = AzureADService()
    token = 'other_error_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'Erro ao validar token Azure AD' in str(exc_info.value.detail)
