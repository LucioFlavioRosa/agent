import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.mark.asyncio
def test_auth_login_accepts_email_and_empresa(client):
    # Testa que o endpoint /auth/login aceita email e empresa e retorna user_info corretamente
    payload = {
        "email": "user@example.com",
        "empresa": "Peers"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "user_info" in data
    assert data["user_info"]["email"] == payload["email"]
    assert data["user_info"]["empresa"] == payload["empresa"]
    assert "projects" in data
    assert isinstance(data["projects"], list)

@pytest.mark.asyncio
def test_auth_login_missing_fields(client):
    # Testa que falta de email ou empresa retorna erro
    payload = {"email": "user@example.com"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 400
    assert "detail" in response.json()
    payload = {"empresa": "Peers"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 400
    assert "detail" in response.json()
    payload = {}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 400
    assert "detail" in response.json()
