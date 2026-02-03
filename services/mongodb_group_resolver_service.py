from pymongo import MongoClient
from typing import Optional
from models.user_group_mapping import UserGroupMapping
from tools.azure_secret_manager import AzureSecretManager, VaultType
import os

class MongoDBGroupResolverService:
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None, vault_type: VaultType = VaultType.DEFAULT, collection_name: Optional[str] = None):
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=vault_type)
        self.collection_name = collection_name or os.getenv('AZURE_MONGODB_GROUP_COLLECTION', 'user_group_mappings')
        self.mongo_connection_string = self._get_mongo_connection_string()
        self.client = MongoClient(self.mongo_connection_string)
        self.db_name = os.getenv('AZURE_MONGODB_DATABASE', 'default_db')
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def _get_mongo_connection_string(self) -> str:
        secret_name = 'azure-mongodb-connection-string'
        # O padrão de secret é nome-grupo-empresa, mas para connection string é global (sem contexto de usuário)
        try:
            connection_string = self.secret_manager.get_secret(secret_name)
            if not connection_string:
                raise ValueError(f"Connection string MongoDB '{secret_name}' não encontrada no Key Vault.")
            return connection_string
        except Exception as e:
            raise RuntimeError(f"Erro ao obter connection string do MongoDB: {e}")

    def get_group_for_user(self, usuario: str, empresa: str) -> str:
        query = {"usuario": usuario, "empresa": empresa}
        result = self.collection.find_one(query)
        if not result or 'grupo' not in result:
            raise ValueError(f"Grupo não encontrado para usuario='{usuario}' e empresa='{empresa}' no MongoDB. Sem fallback.")
        return result['grupo']
