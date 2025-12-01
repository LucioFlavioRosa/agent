from pydantic import BaseModel, Field
from typing import Optional

class KeyVaultConfig(BaseModel):
    azure_kv_url: Optional[str] = Field(None, description="URL do Key Vault para segredos do ambiente Azure.")
    devops_kv_url: Optional[str] = Field(None, description="URL do Key Vault para segredos do Azure DevOps.")
    github_kv_url: Optional[str] = Field(None, description="URL do Key Vault para segredos do GitHub.")
    llm_kv_url: Optional[str] = Field(None, description="URL do Key Vault para segredos de APIs de LLM.")
