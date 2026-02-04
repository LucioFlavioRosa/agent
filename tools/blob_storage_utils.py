from tools.user_email_parser import UserEmailParser

def get_blob_container_name(secret_manager, user_email, group_resolver):
    """
    Obtém o nome do container do Blob Storage.
    """
    if group_resolver is None:
        raise ValueError("group_resolver não pode ser None para obter o nome do container.")
    
    grupo = group_resolver.get_group_for_user(user_email)
    _, empresa = UserEmailParser.parse_email(user_email)
    
    # Exemplo: azure-storage-container-name-admin-peers
    secret_name = f"azure-storage-container-name-{grupo}-{empresa}"
    
    try:
        container_name = secret_manager.get_secret(secret_name)
        if not container_name or not isinstance(container_name, str):
            raise RuntimeError(f"Secret '{secret_name}' não encontrado ou vazio.")
        return container_name
    except Exception as e:
        raise RuntimeError(f"Erro ao recuperar container via secret '{secret_name}': {e}")

# --- CORREÇÃO AQUI EMBAIXO ---
def get_blob_connection_string(secret_manager, user_email, group_resolver=None):
    """
    Obtém a Connection String.
    Aceita 'group_resolver' como argumento opcional para evitar erro de chamada, 
    mesmo que não seja usado na lógica da string de conexão.
    """
    usuario, empresa = UserEmailParser.parse_email(user_email)
    
    # Sanitização: troca '.' por '-'
    usuario_sanitizado = usuario.replace('.', '-')
    
    # Exemplo: azure-storage-connection-string-lucio-rosa-peers
    
    secret_name = "azure-storage-connection-string"
    
    try:
        conn_string = secret_manager.get_secret(secret_name)
        if not conn_string:
            raise ValueError(f"Connection String não encontrada no secret '{secret_name}'.")
        return conn_string
    except Exception as e:
        print(f"[BlobUtils] Erro ao buscar secret '{secret_name}': {e}")
        raise e
