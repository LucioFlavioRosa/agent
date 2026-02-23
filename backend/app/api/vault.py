from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Supondo que VaultService está implementado em outro módulo
from backend.app.services.vault_service import vault_service, VaultSecretNotFoundError

router = APIRouter()

class VaultKeyRequest(BaseModel):
    vault_type: str  # Exemplo: 'azure', 'llm', 'project'
    key_name: str    # Exemplo: 'blobstorage-connection-string', 'openai-api-key'
    company_id: str
    group_id: Optional[str] = None

class VaultKeyResponse(BaseModel):
    key_name: str
    value_preview: str  # Apenas os primeiros 4 caracteres + '***'

@router.post("/api/v1/vault/test-secret", response_model=VaultKeyResponse)
def test_secret(req: VaultKeyRequest):
    try:
        secret_value = vault_service.get_secret(
            vault_type=req.vault_type,
            key_name=req.key_name,
            company_id=req.company_id,
            group_id=req.group_id
        )
        preview = (secret_value[:4] + '***') if secret_value else '***'
        return VaultKeyResponse(key_name=req.key_name, value_preview=preview)
    except VaultSecretNotFoundError:
        raise HTTPException(status_code=404, detail="Secret not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
