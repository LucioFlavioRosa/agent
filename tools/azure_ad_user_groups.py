import os
from typing import List
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
import requests

def get_user_groups(email: str) -> List[str]:
    try:
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        
        if not all([tenant_id, client_id, client_secret]):
            print("[Azure AD] Credenciais não configuradas, retornando lista vazia")
            return []
        
        credential = DefaultAzureCredential()
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        access_token = token_response.json()['access_token']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        user_url = f"https://graph.microsoft.com/v1.0/users/{email}"
        user_response = requests.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_id = user_response.json()['id']
        
        groups_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf"
        groups_response = requests.get(groups_url, headers=headers)
        groups_response.raise_for_status()
        
        groups_data = groups_response.json()
        group_names = []
        
        for group in groups_data.get('value', []):
            if group.get('@odata.type') == '#microsoft.graph.group':
                group_names.append(group.get('displayName', ''))
        
        print(f"[Azure AD] Grupos encontrados para {email}: {group_names}")
        return group_names
        
    except ClientAuthenticationError as e:
        print(f"[Azure AD] Erro de autenticação: {e}")
        return []
    except HttpResponseError as e:
        print(f"[Azure AD] Erro HTTP: {e}")
        return []
    except requests.RequestException as e:
        print(f"[Azure AD] Erro de requisição: {e}")
        return []
    except Exception as e:
        print(f"[Azure AD] Erro inesperado: {e}")
        return []