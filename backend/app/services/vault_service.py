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

    # 🚀 NOVO PARÂMETRO 'vault_type' (Padrão é 'llm', pois será o mais usado aqui)
    # 🚀 ADICIONADO PARÂMETRO 'is_global' (padrão False)
    async def get_secret(
        self, 
        base_name: str, 
        company_id: str = None, 
        group_id: Optional[str] = None, 
        vault_type: str = "llm",
        is_global: bool = False
    ) -> Optional[str]:
        target_url = self.vaults.get(vault_type)
        if not target_url:
            logger.error(f"vault_secret_erro | Cofre do tipo '{vault_type}' não configurado nas variáveis de ambiente.")
            return None

        logger.info(f"vault_secret_busca_iniciada | base_name={base_name} | target_vault={vault_type} | is_global={is_global}")

        # 🚀 SE FOR GLOBAL, BUSCA EXATAMENTE O BASE_NAME
        if is_global:
            names_to_try = [base_name]
        else:
            if not company_id:
                logger.error("vault_secret_erro | company_id é obrigatório quando is_global=False.")
                return None
                
            safe_company_id = self._sanitize_name(company_id)
            safe_group_id = self._sanitize_name(group_id) if group_id else None
            
            secret_name_full = f"{base_name}-{safe_company_id}-{safe_group_id}" if safe_group_id else f"{base_name}-{safe_company_id}"
            fallback_secret_name = f"{base_name}-{safe_company_id}"
            
            names_to_try = [secret_name_full]
            if safe_group_id:
                names_to_try.append(fallback_secret_name)
                
        for secret_name in names_to_try:
            # 1. Tenta no Cache
            cached_value = self.cache.get(secret_name)
            if cached_value:
                logger.info(f"vault_secret_encontrado | secret_name={secret_name} | origem=cache")
                return cached_value
                
            # 2. Vai DIRETO no cofre correto
            try:
                async with SecretClient(vault_url=target_url, credential=self.credential) as client:
                    secret = await client.get_secret(secret_name)
                    self.cache.set(secret_name, secret.value)
                    logger.info(f"vault_secret_encontrado | secret_name={secret_name} | vault_url={target_url}")
                    return secret.value
            except ResourceNotFoundError:
                continue 
            except Exception as e:
                logger.error(f"vault_secret_erro_acesso | secret_name={secret_name} | vault_url={target_url} | erro={str(e)}")
                continue
                
        logger.warning(f"vault_secret_nao_encontrado | base_name={base_name} | company_id={company_id}")
        return None

# ============================================================================
# INSTÂNCIA GLOBAL OTIMIZADA
# ============================================================================
vault_service = VaultService(
    infra_url=settings.AZURE_INFRA_VAULT_URL, 
    llm_url=settings.AZURE_LLM_VAULT_URL
)
