import os
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError

class KeyVaultRBACService:
    def __init__(self, keyvault_uri: Optional[str] = None):
        self.keyvault_uri = keyvault_uri or os.getenv("KEYVAULT_URI")
        if not self.keyvault_uri:
            raise ValueError("KEYVAULT_URI deve ser fornecido via parâmetro ou variável de ambiente")
        
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.keyvault_uri, credential=self.credential)
    
    def get_secret_for_group(self, group_name: str, secret_name: str) -> Optional[str]:
        try:
            print(f"[KeyVault RBAC] Buscando secret '{secret_name}' para grupo '{group_name}'")
            
            full_secret_name = f"{group_name}-{secret_name}"
            
            secret = self.client.get_secret(full_secret_name)
            
            print(f"[KeyVault RBAC] Secret '{full_secret_name}' encontrado com sucesso")
            return secret.value
            
        except ResourceNotFoundError:
            print(f"[KeyVault RBAC] Secret '{full_secret_name}' não encontrado no Key Vault")
            return None
        except ClientAuthenticationError as e:
            print(f"[KeyVault RBAC] Erro de autenticação ao acessar Key Vault: {e}")
            return None
        except Exception as e:
            print(f"[KeyVault RBAC] Erro inesperado ao buscar secret '{full_secret_name}': {e}")
            return None
    
    def get_repository_token_for_group(self, group_name: str, repository_type: str) -> Optional[str]:
        try:
            print(f"[KeyVault RBAC] Buscando token de repositório '{repository_type}' para grupo '{group_name}'")
            
            token_secret_name = f"{repository_type}-token"
            return self.get_secret_for_group(group_name, token_secret_name)
            
        except Exception as e:
            print(f"[KeyVault RBAC] Erro ao buscar token de repositório para grupo '{group_name}': {e}")
            return None
    
    def list_secrets_for_group(self, group_name: str) -> list:
        try:
            print(f"[KeyVault RBAC] Listando secrets disponíveis para grupo '{group_name}'")
            
            group_prefix = f"{group_name}-"
            group_secrets = []
            
            for secret_properties in self.client.list_properties_of_secrets():
                if secret_properties.name.startswith(group_prefix):
                    secret_name = secret_properties.name[len(group_prefix):]
                    group_secrets.append(secret_name)
            
            print(f"[KeyVault RBAC] Secrets encontrados para grupo '{group_name}': {group_secrets}")
            return group_secrets
            
        except Exception as e:
            print(f"[KeyVault RBAC] Erro ao listar secrets para grupo '{group_name}': {e}")
            return []

def get_secret_for_group(group_name: str, secret_name: str, keyvault_uri: Optional[str] = None) -> Optional[str]:
    service = KeyVaultRBACService(keyvault_uri)
    return service.get_secret_for_group(group_name, secret_name)

def get_repository_token_for_group(group_name: str, repository_type: str, keyvault_uri: Optional[str] = None) -> Optional[str]:
    service = KeyVaultRBACService(keyvault_uri)
    return service.get_repository_token_for_group(group_name, repository_type)