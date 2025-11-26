import pytest
from fastapi import FastAPI, Request, HTTPException
from starlette.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from unittest.mock import patch, MagicMock

# Supondo que AuthMiddleware e AzureADService estão em backend/app/middleware/auth_middleware.py
from backend.app.middleware.auth_middleware import AuthMiddleware

class MockAzureADService:
    @staticmethod
    def validate_token(token: str):
        if token == "valid-token":
            return {"usuario_executor": "user123", "sub": "user123"}
        elif token == "invalid-token":
            raise HTTPException(status_code=401, detail="Token inválido.")
        elif token == "expired-token":
            raise HTTPException(status_code=401, detail="Token expirado.")
        return None

# App para testes
def get_test_app():
    app = FastAPI()

    @app.get("/protected")
    async def protected(request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não autenticado.")
        return {"usuario_executor": user.get("usuario_executor")}

    app.add_middleware(AuthMiddleware)
    return app

@pytest.fixture
def client():
    app = get_test_app()
    return TestClient(app)

@patch("backend.app.middleware.auth_middleware.AzureADService", new=MockAzureADService)
def test_valid_token_injects_user(client):
    response = client.get("/protected", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["usuario_executor"] == "user123"

@patch("backend.app.middleware.auth_middleware.AzureADService", new=MockAzureADService)
def test_invalid_token_returns_401(client):
    response = client.get("/protected", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert "Token inválido" in response.json()["detail"]

@patch("backend.app.middleware.auth_middleware.AzureADService", new=MockAzureADService)
def test_expired_token_returns_401(client):
    response = client.get("/protected", headers={"Authorization": "Bearer expired-token"})
    assert response.status_code == 401
    assert "Token expirado" in response.json()["detail"]

@patch("backend.app.middleware.auth_middleware.AzureADService", new=MockAzureADService)
def test_missing_token_returns_401(client):
    response = client.get("/protected")
    assert response.status_code == 401
    assert "Usuário não autenticado" in response.json()["detail"]
