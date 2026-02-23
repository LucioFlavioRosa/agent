from typing import Optional, Literal
from pydantic import BaseModel

class VaultKeyRequest(BaseModel):
    key_base_name: str
    company_id: str
    group_id: Optional[str] = None
    vault_type: Literal["infrastructure", "llm", "integrations"]

class VaultKeyResponse(BaseModel):
    key_name: str
    value: str
