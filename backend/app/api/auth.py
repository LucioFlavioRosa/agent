from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from typing import Optional
import msal
import os
from datetime import datetime, timedelta

router = APIRouter()

# Configurações Azure AD
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "<your-client-id>")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "<your-tenant-id>")
AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "<your-client-secret>")
AZURE_SCOPE = [os.environ.get("AZURE_SCOPE", "User.Read")]

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Autenticação via Azure AD
@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    app = msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AZURE_AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET
    )
    result = app.acquire_token_by_username_password(
        username=request.username,
        password=request.password,
        scopes=AZURE_SCOPE
    )
    if "access_token" not in result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falha na autenticação Azure AD: {result.get('error_description', 'Erro desconhecido')}"
        )
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result.get("expires_in", 3600)
    )
