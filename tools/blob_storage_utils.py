from tools.user_email_parser import UserEmailParser

def get_blob_container_name(secret_manager, user_email, group_resolver):
    """
    Obtém o nome do container do Blob Storage a partir do cofre Azure.
    Secret esperado: 'azure-storage-container-name-{grupo}-{empresa}'
    """
    if group_resolver is None:
        raise ValueError("group_resolver não pode ser None para obter o nome do container do Blob Storage.")
    
    grupo = group_resolver.get_group_for_user(user_email)
    _, empresa = UserEmailParser.parse_email(user_email)
    
    # Exemplo: azure-storage-container-name-admin-peers
    secret_name = f"azure-storage-container-name-{grupo}-{empresa}"
    
    try:
        container_name = secret_manager.get_secret(secret_name)
        if not container_name or not isinstance(container_name, str):
            raise RuntimeError(f"Secret '{secret_name}' não encontrado ou vazio no Azure Key Vault.")
        return container_name
    except Exception as e:
        raise RuntimeError(f"Erro ao recuperar o nome do container via secret '{secret_name}': {e}")

def get_blob_connection_string(secret_manager, user_email):
    """
    Obtém a Connection String do Storage Account.
    Secret esperado: 'azure-storage-connection-string-{usuario_sanitizado}-{empresa}'
    """
    usuario, empresa = UserEmailParser.parse_email(user_email)
    
    # --- IMPORTANTE: Sanitização do nome (troca '.' por '-') ---
    # O Key Vault não aceita pontos. 'lucio.rosa' vira 'lucio-rosa'
    usuario_sanitizado = usuario.replace('.', '-')
    
    # Exemplo: azure-storage-connection-string-lucio-rosa-peers
    secret_name = f"azure-storage-connection-string-{usuario_sanitizado}-{empresa}"
    
    try:
        conn_string = secret_manager.get_secret(secret_name)
        if not conn_string:
            raise ValueError(f"Connection String não encontrada no secret '{secret_name}'.")
        return conn_string
    except Exception as e:
        # Loga o erro mas relança para ser tratado quem chamou
        print(f"[BlobUtils] Erro ao buscar secret '{secret_name}': {e}")
        raise e
