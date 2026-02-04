import os
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient
from redis import Redis
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from tools.azure_secret_manager import AzureSecretManager, VaultType

load_dotenv()

# Variáveis de ambiente obrigatórias
REQUIRED_ENV_VARS = [
    "AZURE_KEY_VAULT_LLM_URL",
    "AZURE_KEY_VAULT_REPOSITORY_URL",
    "AZURE_KEY_VAULT_BLOB_STORAGE_URL",
    "MONGODB_CONNECTION_STRING_SECRET_NAME",
    "MONGODB_DATABASE_NAME",
    "MONGODB_COLLECTION_NAME",
    "REDIS_HOST",
    "REDIS_PORT"
]

@pytest.mark.integration
def test_environment_setup():
    missing_env = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    assert not missing_env, f"Variáveis de ambiente obrigatórias ausentes: {missing_env}"

    # Redis connection
    try:
        redis_host = os.getenv("REDIS_HOST")
        redis_port = int(os.getenv("REDIS_PORT"))
        redis_client = Redis(host=redis_host, port=redis_port, socket_connect_timeout=5)
        assert redis_client.ping(), "Não foi possível conectar ao Redis. Verifique host/porta."
    except Exception as e:
        pytest.fail(f"Falha ao conectar ao Redis: {e}")

    # MongoDB connection and test document
    try:
        secret_manager_llm = AzureSecretManager(vault_type=VaultType.LLM)
        mongo_conn_secret_name = os.getenv("MONGODB_CONNECTION_STRING_SECRET_NAME")
        mongo_conn_str = secret_manager_llm.get_secret(mongo_conn_secret_name)
        mongo_db_name = os.getenv("MONGODB_DATABASE_NAME")
        mongo_col_name = os.getenv("MONGODB_COLLECTION_NAME")
        mongo_client = MongoClient(mongo_conn_str, serverSelectionTimeoutMS=5000)
        db = mongo_client[mongo_db_name]
        collection = db[mongo_col_name]
        doc = collection.find_one()
        assert doc is not None, "Nenhum documento encontrado na collection de grupos do MongoDB."
    except Exception as e:
        pytest.fail(f"Falha ao conectar ao MongoDB ou buscar documento: {e}")

    # Azure Key Vaults: LLM, Repository, Blob Storage
    vault_envs = [
        (VaultType.LLM, os.getenv("AZURE_KEY_VAULT_LLM_URL")),
        (VaultType.REPOSITORY, os.getenv("AZURE_KEY_VAULT_REPOSITORY_URL")),
        (VaultType.BLOB_STORAGE, os.getenv("AZURE_KEY_VAULT_BLOB_STORAGE_URL"))
    ]
    credential = DefaultAzureCredential()
    for vault_type, vault_url in vault_envs:
        try:
            assert vault_url, f"URL do Key Vault para {vault_type.name} não definida."
            client = SecretClient(vault_url=vault_url, credential=credential)
            secrets = [s.name for s in client.list_properties_of_secrets()]
            assert secrets, f"Nenhum secret encontrado no Key Vault: {vault_url}"
        except Exception as e:
            pytest.fail(f"Falha ao acessar Key Vault ({vault_type.name}): {e}")

    # AzureSecretManager instanciável para cada VaultType
    for vault_type in VaultType:
        try:
            manager = AzureSecretManager(vault_type=vault_type)
            assert manager is not None, f"Falha ao instanciar AzureSecretManager para {vault_type.name}"
        except Exception as e:
            pytest.fail(f"Falha ao instanciar AzureSecretManager para {vault_type.name}: {e}")
