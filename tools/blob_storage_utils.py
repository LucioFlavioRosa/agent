from tools.user_email_parser import UserEmailParser

def get_blob_container_name(secret_manager, user_email, group_resolver):
    """
    Obtém o nome do container do Blob Storage a partir do cofre Azure, usando o grupo do MongoDB e a empresa do e-mail.
    O nome do secret é 'azure-storage-container-name-{grupo}-{empresa}'.
    Retorna o valor do secret, que é o nome do container.
    Lança exceção se o secret não existir ou se group_resolver for None.
    """
    if group_resolver is None:
        raise ValueError("group_resolver não pode ser None para obter o nome do container do Blob Storage.")
    grupo = group_resolver.get_group_for_user(user_email)
    _, empresa = UserEmailParser.parse_email(user_email)
    secret_name = f"azure-storage-container-name-{grupo}-{empresa}"
    try:
        container_name = secret_manager.get_secret(secret_name)
        if not container_name or not isinstance(container_name, str):
            raise RuntimeError(f"Secret '{secret_name}' não encontrado ou vazio no Azure Key Vault.")
        return container_name
    except Exception as e:
        raise RuntimeError(f"Erro ao recuperar o nome do container do Blob Storage via secret '{secret_name}': {e}")
