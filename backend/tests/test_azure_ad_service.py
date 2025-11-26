import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

# Supondo que AzureADService e AzureADTokenData estejam em backend/services/azure_ad_service.py
from backend.services.azure_ad_service import AzureADService, AzureADTokenData

class DummyToken:
    def __init__(self, claims):
        self.claims = claims

@patch('backend.services.azure_ad_service.DefaultAzureCredential')
@patch('backend.services.azure_ad_service.decode_jwt')
def test_validate_token_valid(mock_decode_jwt, mock_credential):
    # Simula token válido
    claims = {
        'usuario_executor': 'user1',
        'exp': 9999999999,
        'sub': 'user1',
        'iss': 'https://login.microsoftonline.com/',
        'aud': 'api://backend-app'
    }
    mock_decode_jwt.return_value = claims
    service = AzureADService()
    token = 'valid_token'
    result = service.validate_token(token)
    assert isinstance(result, AzureADTokenData)
    assert result.usuario_executor == 'user1'
    assert result.sub == 'user1'
    assert result.exp == 9999999999
    assert result.iss == 'https://login.microsoftonline.com/'
    assert result.aud == 'api://backend-app'

@patch('backend.services.azure_ad_service.DefaultAzureCredential')
@patch('backend.services.azure_ad_service.decode_jwt')
def test_validate_token_invalid(mock_decode_jwt, mock_credential):
    # Simula token inválido (raise Exception)
    mock_decode_jwt.side_effect = Exception('Invalid token')
    service = AzureADService()
    token = 'invalid_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'Token inválido' in str(exc_info.value.detail)

@patch('backend.services.azure_ad_service.DefaultAzureCredential')
@patch('backend.services.azure_ad_service.decode_jwt')
def test_validate_token_expired(mock_decode_jwt, mock_credential):
    # Simula token expirado
    claims = {
        'usuario_executor': 'user1',
        'exp': 1,  # timestamp passado
        'sub': 'user1'
    }
    mock_decode_jwt.return_value = claims
    service = AzureADService()
    token = 'expired_token'
    with pytest.raises(HTTPException) as exc_info:
        service.validate_token(token)
    assert exc_info.value.status_code == 401
    assert 'Token expirado' in str(exc_info.value.detail)
