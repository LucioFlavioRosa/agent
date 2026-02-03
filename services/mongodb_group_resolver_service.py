from pymongo import MongoClient
from typing import Optional
from models.user_group_mapping import UserGroupMapping
from tools.azure_secret_manager import AzureSecretManager, VaultType
import os

class MongoDBGroupResolverService:
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None, vault_type: VaultType = VaultType.AZURE_INFRASTRUCTURE, collection_name: Optional[str] = None):
        # Sempre usar o cofre de infraestrutura Azure para segredos do MongoDB
        self.secret_manager = AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE)
        self.collection_name = os.getenv('AZURE_MONGODB_GROUP_COLLECTION')
        self.mongo_connection_string = self._get_mongo_connection_string()
        self.client = MongoClient(self.mongo_connection_string)
        self.db_name = os.getenv('AZURE_MONGODB_DATABASE')
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def _get_mongo_connection_string(self) -> str:
        secret_name = 'azure-mongodb-connection-string'
        try:
            connection_string = self.secret_manager.get_secret(secret_name)
            if not connection_string:
                raise ValueError(f"Connection string MongoDB '{secret_name}' não encontrada no Key Vault de infraestrutura Azure.")
            return connection_string
        except Exception as e:
            raise RuntimeError(f"Erro ao obter connection string do MongoDB: {e}")

    def get_group_for_user(self, usuario: str, empresa: str) -> str:
        query = {"usuario": usuario, "empresa": empresa}
        result = self.collection.find_one(query)
        if not result or 'grupo' not in result:
            raise ValueError(f"Grupo não encontrado para usuario='{usuario}' e empresa='{empresa}' no MongoDB. Sem fallback.")
        return result['grupo']
