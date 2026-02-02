from typing import Optional
from domain.interfaces.secret_manager_interface import ISecretManager
import os

def get_blob_connection_string(secret_manager: Optional[ISecretManager] = None) -> str:
    """
    Obtém a connection string do Azure Blob Storage, tentando primeiro o Key Vault via secret_manager,
    e depois a variável de ambiente AZURE_STORAGE_CONNECTION_STRING.
    """
    secret_name = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    connection_string = None
    if secret_manager is not None and secret_name:
        try:
            connection_string = secret_manager.get_secret(secret_name)
        except Exception as e:
            print(f"[blob_storage_utils] Warning: Failed to get connection string from Key Vault: {e}")
    if not connection_string:
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connection_string:
        raise RuntimeError('Azure Blob Storage connection string not found in Key Vault or environment variables.')
    return connection_string
