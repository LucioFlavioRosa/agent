from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Supondo que VaultService está implementado em outro módulo
from backend.app.services.vault_service import vault_service

router = APIRouter()

class VaultKeyRequest(BaseModel):
    vault_type: str  # Exemplo: 'azure', 'llm', 'project'
    key_name: str    # Exemplo: 'blobstorage-connection-string', 'openai-api-key'
    company_id: str
    group_id: Optional[str] = None

class VaultKeyResponse(BaseModel):
    key_name: str
    value_preview: str  # Apenas os primeiros 4 caracteres + '***'
