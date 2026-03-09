import time
import logging
import re
import traceback
import asyncio
from typing import Optional, List
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger("mcp_vault")

class VaultCache:
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
    def __init__(self, vault_urls: List[str]):
        self.vault_urls = vault_urls
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
        company_id: str = "default", 
        group_id: Optional[str] = None,
        vault_type: str = "infra", # Adicionado para compatibilidade
        is_global: bool = False    # 🚀 ESSENCIAL: Para nomes exatos como chaves de fila/AWS
    ) -> Optional[str]:
        
        # 1. Define a estratégia de nomes
        if is_global:
            # Se for global, tenta apenas o nome exato (ex: queue-connection-string)
            names_to_try = [base_name]
        else:
            # Estratégia de fallback: Grupo -> Empresa
            safe_company_id = self._sanitize_name(company_id)
            safe_group_id = self._sanitize_name(group_id) if group_id else None
            
            names_to_try = []
            if safe_group_id:
                names_to_try.append(f"{base_name}-{safe_company_id}-{safe_group_id}")
            
            names_to_try.append(f"{base_name}-{safe_company_id}")

        print(f"🔍 [VAULT] Procurando segredo: {base_name} (Global={is_global})", flush=True)

        for secret_name in names_to_try:
            # Tenta o Cache
            cached_value = self.cache.get(secret_name)
            if cached_value:
                return cached_value

            # Tenta nos Cofres configurados
            for url in self.vault_urls:
                try:
                    async with SecretClient(vault_url=url, credential=self.credential) as client:
                        secret = await client.get_secret(secret_name)
                        self.cache.set(secret_name, secret.value)
                        print(f"✅ [VAULT] Segredo '{secret_name}' encontrado.", flush=True)
                        return secret.value
                except ResourceNotFoundError:
                    # Avisa apenas no log de debug se não achou no primeiro nome da lista
                    continue
                except Exception as e:
                    print(f"⚠️ [VAULT] Erro ao acessar cofre {url}: {e}", flush=True)
                    continue
        
        print(f"❌ [VAULT] Segredo '{base_name}' não encontrado em nenhum cofre.", flush=True)
        return None
