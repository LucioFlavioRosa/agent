import json
import os
from typing import List, Dict, Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class KeyVaultRBACService:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.keyvault_url = os.getenv("AZURE_KEY_VAULT_URL", "https://your-keyvault.vault.azure.net/")
        self.secret_client = SecretClient(vault_url=self.keyvault_url, credential=self.credential)
        self._group_token_mapping = self._load_group_token_mapping()
    
    def _load_group_token_mapping(self) -> Dict[str, List[str]]:
        default_mapping = {
            "DevOps-Admin": ["github-token", "gitlab-token", "azure-token"],
            "DevOps-Developer": ["github-token", "gitlab-token"],
            "DevOps-ReadOnly": ["github-token"],
            "Azure-Admin": ["azure-token"],
            "GitLab-Team": ["gitlab-token"],
            "GitHub-Team": ["github-token"]
        }
        
        try:
            mapping_secret = self.secret_client.get_secret("rbac-group-token-mapping")
            custom_mapping = json.loads(mapping_secret.value)
            print(f"[KeyVault RBAC] Mapeamento customizado carregado do Key Vault")
            return custom_mapping
        except Exception as e:
            print(f"[KeyVault RBAC] Usando mapeamento padrão. Erro ao carregar do Key Vault: {e}")
            return default_mapping
    
    def get_allowed_tokens_for_groups(self, groups: List[str]) -> List[str]:
        allowed_tokens = set()
        
        for group in groups:
            if group in self._group_token_mapping:
                tokens = self._group_token_mapping[group]
                allowed_tokens.update(tokens)
                print(f"[KeyVault RBAC] Grupo '{group}' tem acesso aos tokens: {tokens}")
            else:
                print(f"[KeyVault RBAC] Grupo '{group}' não encontrado no mapeamento")
        
        allowed_tokens_list = list(allowed_tokens)
        print(f"[KeyVault RBAC] Tokens permitidos consolidados: {allowed_tokens_list}")
        return allowed_tokens_list
    
    def get_allowed_token_for_repository_type(self, groups: List[str], repository_type: str) -> Optional[str]:
        allowed_tokens = self.get_allowed_tokens_for_groups(groups)
        
        token_mapping = {
            "github": "github-token",
            "gitlab": "gitlab-token",
            "azure": "azure-token"
        }
        
        required_token = token_mapping.get(repository_type)
        if not required_token:
            print(f"[KeyVault RBAC] Tipo de repositório '{repository_type}' não reconhecido")
            return None
        
        if required_token in allowed_tokens:
            print(f"[KeyVault RBAC] Usuário autorizado para token '{required_token}' do tipo '{repository_type}'")
            return required_token
        else:
            print(f"[KeyVault RBAC] Usuário NÃO autorizado para token '{required_token}' do tipo '{repository_type}'")
            return None
    
    def validate_user_access_to_repository(self, groups: List[str], repository_type: str, repository_name: str) -> bool:
        allowed_token = self.get_allowed_token_for_repository_type(groups, repository_type)
        
        if not allowed_token:
            return False
        
        org_specific_tokens = [token for token in self.get_allowed_tokens_for_groups(groups) 
                              if token.startswith(f"{repository_type}-token-")]
        
        if org_specific_tokens:
            org_name = self._extract_org_name(repository_name, repository_type)
            expected_token = f"{repository_type}-token-{org_name}"
            if expected_token in org_specific_tokens:
                print(f"[KeyVault RBAC] Acesso específico autorizado para organização '{org_name}'")
                return True
            else:
                print(f"[KeyVault RBAC] Acesso específico NÃO autorizado para organização '{org_name}'")
                return False
        
        return True
    
    def _extract_org_name(self, repository_name: str, repository_type: str) -> str:
        if repository_type == "azure":
            parts = repository_name.split('/')
            return parts[0] if len(parts) >= 3 else "default"
        else:
            parts = repository_name.split('/')
            return parts[0] if len(parts) >= 2 else "default"

def get_allowed_tokens_for_groups(groups: List[str]) -> List[str]:
    service = KeyVaultRBACService()
    return service.get_allowed_tokens_for_groups(groups)

def get_allowed_token_for_repository_type(groups: List[str], repository_type: str) -> Optional[str]:
    service = KeyVaultRBACService()
    return service.get_allowed_token_for_repository_type(groups, repository_type)

def validate_user_access_to_repository(groups: List[str], repository_type: str, repository_name: str) -> bool:
    service = KeyVaultRBACService()
    return service.validate_user_access_to_repository(groups, repository_type, repository_name)