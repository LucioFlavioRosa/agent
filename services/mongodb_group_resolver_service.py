from pymongo import MongoClient
from typing import Optional
import os
import sys  # Importado para forçar o flush do log

# Imports do seu projeto
from models.user_group_mapping import UserGroupMapping
from tools.azure_secret_manager import AzureSecretManager, VaultType

class MongoDBGroupResolverService:
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None, vault_type: VaultType = VaultType.AZURE_INFRASTRUCTURE, collection_name: Optional[str] = None):
        print("--- [MONGO-DEBUG] Iniciando MongoDBGroupResolverService ---", flush=True)
        
        self.secret_manager = AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE)
        
        # 1. Rastrear Variáveis de Ambiente
        self.collection_name = os.getenv('AZURE_MONGODB_GROUP_COLLECTION')
        self.db_name = os.getenv('AZURE_MONGODB_DATABASE')
        
        print(f"[MONGO-DEBUG] Env Var DB: '{self.db_name}'", flush=True)
        print(f"[MONGO-DEBUG] Env Var Collection: '{self.collection_name}'", flush=True)

        if not self.db_name or not self.collection_name:
            print("[MONGO-CRÍTICO] Variáveis de ambiente do Mongo estão vazias!", flush=True)

        # 2. Rastrear Connection String
        print("[MONGO-DEBUG] Tentando obter Connection String do Key Vault...", flush=True)
        self.mongo_connection_string = self._get_mongo_connection_string()
        
        # Mascarando a senha para logar
        if self.mongo_connection_string:
            masked_conn = self.mongo_connection_string[:15] + "..."
            print(f"[MONGO-DEBUG] Connection String obtida: {masked_conn}", flush=True)
        else:
            print("[MONGO-CRÍTICO] Connection String veio vazia/None!", flush=True)

        try:
            self.client = MongoClient(self.mongo_connection_string)
            # Teste rápido de conexão (opcional, mas bom para garantir)
            # self.client.admin.command('ping') 
            # print("[MONGO-DEBUG] Ping no MongoDB com sucesso.", flush=True)
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            print("[MONGO-DEBUG] Conexão com Collection estabelecida.", flush=True)
        except Exception as e:
            print(f"[MONGO-CRÍTICO] Erro ao conectar cliente Mongo: {str(e)}", flush=True)
            raise e

    def _get_mongo_connection_string(self) -> str:
        secret_name = 'azure-mongodb-connection-string'
        try:
            connection_string = self.secret_manager.get_secret(secret_name)
            if not connection_string:
                raise ValueError(f"Connection string MongoDB '{secret_name}' não encontrada no Key Vault de infraestrutura Azure.")
            return connection_string
        except Exception as e:
            print(f"[MONGO-ERRO] Falha ao pegar secret: {e}", flush=True)
            raise RuntimeError(f"Erro ao obter connection string do MongoDB: {e}")

    def get_group_for_user(self, usuario_email: str) -> str:
        """
        Recebe o email completo do usuário e retorna o grupo correspondente consultando o MongoDB.
        """
        print(f"\n--- [MONGO-QUERY] Iniciando busca para: '{usuario_email}' ---", flush=True)
        
        # 3. Verificar limpeza do input (espaços em branco, etc)
        if not usuario_email:
             print("[MONGO-ERRO] Email recebido é None ou Vazio.", flush=True)
        
        # Importante: Mongo é case-sensitive. Verificar se no banco está minúsculo.
        query = {"usuario": usuario_email}
        print(f"[MONGO-QUERY] Query enviada: {query}", flush=True)
        
        try:
            result = self.collection.find_one(query)
            print(f"[MONGO-QUERY] Resultado RAW do banco: {result}", flush=True)

            if not result:
                print(f"[MONGO-ALERTA] Nenhum documento encontrado para '{usuario_email}'.", flush=True)
                # Dica de Debug: Tenta buscar sem filtro para ver se a collection tem algo
                # count = self.collection.count_documents({})
                # print(f"[MONGO-DEBUG] Total de documentos na collection: {count}", flush=True)
                raise ValueError(f"Grupo não encontrado para usuario_email='{usuario_email}' no MongoDB. Sem fallback.")
            
            if 'grupo' not in result:
                print(f"[MONGO-ALERTA] Documento encontrado, mas campo 'grupo' não existe. Chaves disponíveis: {list(result.keys())}", flush=True)
                raise ValueError(f"Campo 'grupo' ausente no documento do usuário '{usuario_email}'.")

            grupo_encontrado = result['grupo']
            print(f"[MONGO-SUCESSO] Grupo retornado: '{grupo_encontrado}'", flush=True)
            return grupo_encontrado

        except Exception as e:
            print(f"[MONGO-EXCEPTION] Erro durante a busca: {str(e)}", flush=True)
            raise e
