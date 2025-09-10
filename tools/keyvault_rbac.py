from typing import List, Optional
from tools.azure_ad_groups import get_user_groups
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

class KeyVaultRBACService:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.keyvault_url = os.getenv('AZURE_KEYVAULT_URI', 'https://your-keyvault.vault.azure.net/')
        self.client = SecretClient(vault_url=self.keyvault_url, credential=self.credential)
        
        self.group_token_mapping = {
            'DevOps-Team': ['github-token', 'gitlab-token', 'azure-devops-token'],
            'Developers': ['github-token', 'gitlab-token'],
            'QA-Team': ['github-token'],
            'Admins': ['github-token', 'gitlab-token', 'azure-devops-token', 'admin-token']
        }
    
    def get_accessible_tokens(self, user_email: str) -> List[str]:
        try:
            print(f"[KeyVault RBAC] Verificando tokens acessíveis para usuário: {user_email}")
            
            user_groups = get_user_groups(user_email)
            if not user_groups:
                print(f"[KeyVault RBAC] Usuário {user_email} não pertence a nenhum grupo")
                return []
            
            accessible_tokens = set()
            
            for group in user_groups:
                tokens_for_group = self.group_token_mapping.get(group, [])
                accessible_tokens.update(tokens_for_group)
                print(f"[KeyVault RBAC] Grupo '{group}' concede acesso aos tokens: {tokens_for_group}")
            
            accessible_tokens_list = list(accessible_tokens)
            print(f"[KeyVault RBAC] Tokens finais acessíveis para {user_email}: {accessible_tokens_list}")
            
            return accessible_tokens_list
            
        except Exception as e:
            print(f"[KeyVault RBAC] Erro ao determinar tokens acessíveis para {user_email}: {e}")
            return []
    
    def validate_token_access(self, user_email: str, token_name: str) -> bool:
        try:
            accessible_tokens = self.get_accessible_tokens(user_email)
            has_access = token_name in accessible_tokens
            
            print(f"[KeyVault RBAC] Usuário {user_email} {'tem' if has_access else 'não tem'} acesso ao token '{token_name}'")
            return has_access
            
        except Exception as e:
            print(f"[KeyVault RBAC] Erro ao validar acesso ao token '{token_name}' para {user_email}: {e}")
            return False
    
    def get_secret_value(self, user_email: str, secret_name: str) -> Optional[str]:
        try:
            if not self.validate_token_access(user_email, secret_name):
                print(f"[KeyVault RBAC] Acesso negado ao secret '{secret_name}' para usuário {user_email}")
                return None
            
            secret = self.client.get_secret(secret_name)
            print(f"[KeyVault RBAC] Secret '{secret_name}' recuperado com sucesso para {user_email}")
            return secret.value
            
        except Exception as e:
            print(f"[KeyVault RBAC] Erro ao recuperar secret '{secret_name}' para {user_email}: {e}")
            return None

_keyvault_service = None

def get_keyvault_service() -> KeyVaultRBACService:
    global _keyvault_service
    if _keyvault_service is None:
        _keyvault_service = KeyVaultRBACService()
    return _keyvault_service

def get_accessible_tokens(user_email: str) -> List[str]:
    service = get_keyvault_service()
    return service.get_accessible_tokens(user_email)

def validate_token_access(user_email: str, token_name: str) -> bool:
    service = get_keyvault_service()
    return service.validate_token_access(user_email, token_name)

def get_secret_value(user_email: str, secret_name: str) -> Optional[str]:
    service = get_keyvault_service()
    return service.get_secret_value(user_email, secret_name)