import pytest
from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.testclient import TestClient
from unittest.mock import patch, MagicMock

# Supondo que get_current_user e AzureADTokenData estão em backend/app/main.py e backend/app/models/azure_ad_models.py
from backend.app.main import get_current_user
from backend.app.models.azure_ad_models import AzureADTokenData

class MockAzureADService:
    @staticmethod
    def validate_token(token: str):
        if token == "valid-token":
            return AzureADTokenData(oid="oid123", preferred_username="user123", email="user123@example.com", roles=["user"], name="User 123", exp=9999999999, iss="https://login.microsoftonline.com/", aud="api://backend-app", sub="user123")
        elif token == "invalid-token":
            raise HTTPException(status_code=401, detail="Assinatura inválida.")
        elif token == "expired-token":
            raise HTTPException(status_code=401, detail="Token expirado.")
        elif token == "missing-claim-token":
            raise HTTPException(status_code=401, detail="usuario_executor não encontrado no token Azure AD.")
        return None

@pytest.fixture
def app():
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(current_user: AzureADTokenData = Depends(get_current_user)):
        return {"usuario_executor": current_user.preferred_username or current_user.email or current_user.sub}

    return test_app

@pytest.fixture
def client(app):
    return TestClient(app)

@patch("backend.app.main.azure_ad_service", new=MockAzureADService)
def test_valid_token(client):
    response = client.get("/protected", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["usuario_executor"] == "user123"

@patch("backend.app.main.azure_ad_service", new=MockAzureADService)
def test_invalid_token_signature(client):
    response = client.get("/protected", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert "Assinatura inválida" in response.json()["detail"]

@patch("backend.app.main.azure_ad_service", new=MockAzureADService)
def test_expired_token(client):
    response = client.get("/protected", headers={"Authorization": "Bearer expired-token"})
    assert response.status_code == 401
    assert "Token expirado" in response.json()["detail"]

@patch("backend.app.main.azure_ad_service", new=MockAzureADService)
def test_missing_claim_token(client):
    response = client.get("/protected", headers={"Authorization": "Bearer missing-claim-token"})
    assert response.status_code == 401
    assert "usuario_executor não encontrado" in response.json()["detail"]

@patch("backend.app.main.azure_ad_service", new=MockAzureADService)
def test_missing_token_header(client):
    response = client.get("/protected")
    assert response.status_code == 401
    assert "Cabeçalho Authorization ausente ou inválido" in response.json()["detail"]
