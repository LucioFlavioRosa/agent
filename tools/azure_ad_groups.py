import json
import requests
from typing import List, Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureADGroupsService:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self._access_token = None
    
    def _get_access_token(self) -> str:
        if not self._access_token:
            token = self.credential.get_token("https://graph.microsoft.com/.default")
            self._access_token = token.token
        return self._access_token
    
    def _make_graph_request(self, endpoint: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{self.graph_endpoint}{endpoint}", headers=headers)
        
        if response.status_code != 200:
            raise ValueError(f"Erro ao consultar Microsoft Graph API: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_user_groups(self, user_email: str) -> List[str]:
        try:
            print(f"[Azure AD Groups] Buscando grupos para usuário: {user_email}")
            
            user_endpoint = f"/users/{user_email}/memberOf"
            response_data = self._make_graph_request(user_endpoint)
            
            groups = []
            for group in response_data.get("value", []):
                if group.get("@odata.type") == "#microsoft.graph.group":
                    group_name = group.get("displayName")
                    if group_name:
                        groups.append(group_name)
            
            print(f"[Azure AD Groups] Grupos encontrados para {user_email}: {groups}")
            return groups
            
        except Exception as e:
            print(f"[Azure AD Groups] Erro ao buscar grupos para {user_email}: {e}")
            return []
    
    def user_in_group(self, user_email: str, group_name: str) -> bool:
        try:
            print(f"[Azure AD Groups] Verificando se {user_email} pertence ao grupo: {group_name}")
            
            user_groups = self.get_user_groups(user_email)
            is_member = group_name in user_groups
            
            print(f"[Azure AD Groups] Usuário {user_email} {'pertence' if is_member else 'não pertence'} ao grupo {group_name}")
            return is_member
            
        except Exception as e:
            print(f"[Azure AD Groups] Erro ao verificar pertencimento ao grupo {group_name} para {user_email}: {e}")
            return False
    
    def get_user_id_by_email(self, user_email: str) -> Optional[str]:
        try:
            user_endpoint = f"/users/{user_email}"
            response_data = self._make_graph_request(user_endpoint)
            return response_data.get("id")
        except Exception as e:
            print(f"[Azure AD Groups] Erro ao buscar ID do usuário {user_email}: {e}")
            return None

def get_user_groups(user_email: str) -> List[str]:
    service = AzureADGroupsService()
    return service.get_user_groups(user_email)

def check_user_in_group(user_email: str, group_name: str) -> bool:
    service = AzureADGroupsService()
    return service.user_in_group(user_email, group_name)