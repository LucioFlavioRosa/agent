import os
import time
import logging
import re
from typing import Optional, List
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError
from backend.app.config.settings import settings

logger = logging.getLogger("mcp_vault")

class VaultCache:
    """Cache simples com TTL para segredos de cofres (15 minutos)."""
    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: str, ttl: int = 900):
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)

class VaultService:
    def __init__(self, infra_url: str, llm_url: str):
        # 🚀 MAPEAMENTO EXPLÍCITO DE COFRES
        self.vaults = {
            "infra": infra_url,
            "llm": llm_url
        }
        self.credential = DefaultAzureCredential()
        self.cache = VaultCache()

    def _sanitize_name(self, name: str) -> str:
        if not name:
            return name
        sanitized = re.sub(r'[^0-9a-zA-Z-]+', '-', name)
        return sanitized.strip('-')

    async def get_secret(
        self, 
        base_name: str, 
        company_id: str = None, 
        group_id: Optional[str] = None, 
        vault_type: str = "llm",
        is_global: bool = False
    ) -> Optional[str]:
        target_url = self.vaults.get(vault_type)
        print(f"🔍 [VAULT] Iniciando busca: base={base_name}, vault_type={vault_type}, URL={target_url}", flush=True)

        if not target_url:
            print(f"❌ [VAULT] ERRO: A URL do cofre de '{vault_type}' está VAZIA!", flush=True)
            return None

        if is_global:
            names_to_try = [base_name]
        else:
            safe_company_id = self._sanitize_name(company_id)
            safe_group_id = self._sanitize_name(group_id) if group_id else None
            
            secret_name_full = f"{base_name}-{safe_company_id}-{safe_group_id}" if safe_group_id else f"{base_name}-{safe_company_id}"
            fallback_secret_name = f"{base_name}-{safe_company_id}"
            
            names_to_try = [secret_name_full]
            if safe_group_id:
                names_to_try.append(fallback_secret_name)
                
        print(f"🔍 [VAULT] Nomes exatos que vamos procurar na Azure: {names_to_try}", flush=True)

        for secret_name in names_to_try:
            cached_value = self.cache.get(secret_name)
            if cached_value:
                return cached_value
                
            try:
                print(f"⏳ [VAULT] Batendo na porta da Azure para pegar: {secret_name}...", flush=True)
                async with SecretClient(vault_url=target_url, credential=self.credential) as client:
                    secret = await client.get_secret(secret_name)
                    self.cache.set(secret_name, secret.value)
                    print(f"✅ [VAULT] SUCESSO! Achamos a chave: {secret_name}", flush=True)
                    return secret.value
            except ResourceNotFoundError:
                print(f"⚠️ [VAULT] A Azure disse que {secret_name} NÃO EXISTE lá dentro.", flush=True)
                continue 
            except Exception as e:
                # 🚀 O ERRO DE PERMISSÃO VAI GRITAR AQUI!
                print(f"❌ [VAULT] ERRO DE ACESSO/PERMISSÃO AO COFRE: {str(e)}", flush=True)
                continue
                
        print(f"❌ [VAULT] Fim da linha. Nenhuma das chaves foi encontrada.", flush=True)
        return None

# ============================================================================
# INSTÂNCIA GLOBAL OTIMIZADA
# ============================================================================
vault_service = VaultService(
    infra_url=settings.AZURE_INFRA_VAULT_URL, 
    llm_url=settings.AZURE_LLM_VAULT_URL
)
