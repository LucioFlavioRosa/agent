def get_blob_connection_string(secret_manager, user_email: str):
    """
    Obtém a connection string do Azure Blob Storage usando o secret_manager já instanciado.
    O secret_manager deve estar configurado para acessar o cofre dedicado ao Blob Storage.
    """
    secret_name = 'azure-storage-connection-string'
    if not user_email:
        raise ValueError("user_email é obrigatório para buscar a connection string do Blob Storage.")
    try:
        connection_string = secret_manager.get_secret_with_user_context(secret_name, user_email)
        if not connection_string:
            raise ValueError(f"Connection string '{secret_name}' não encontrada para o usuário '{user_email}' no Key Vault de Blob Storage.")
        return connection_string
    except Exception as e:
        print(f"[get_blob_connection_string] Erro ao buscar connection string para usuário '{user_email}': {e}")
        raise
