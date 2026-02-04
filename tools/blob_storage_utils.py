def get_blob_connection_string(secret_manager, user_email: str, group_resolver: object = None, vault_type=None):
    """
    Obtém a connection string do Azure Blob Storage usando o secret_manager já instanciado.
    Busca sempre o secret fixo 'azure-storage-connection-string' no Key Vault.
    """
    secret_name = 'azure-storage-connection-string'
    try:
        connection_string = secret_manager.get_secret(secret_name)
        if not connection_string:
            raise ValueError(f"Connection string '{secret_name}' não encontrada no Key Vault de Blob Storage.")
        return connection_string
    except Exception as e:
        print(f"[get_blob_connection_string] Erro ao buscar connection string: {e}")
        raise
