def get_blob_connection_string(secret_manager):
    """
    Obtém a connection string do Azure Blob Storage usando o secret_manager já instanciado.
    O secret_manager deve estar configurado para acessar o cofre dedicado ao Blob Storage.
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
