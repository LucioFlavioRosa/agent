from tools.azure_secret_manager import VaultType
from tools.user_email_parser import UserEmailParser

def get_blob_connection_string(secret_manager, user_email: str, group_resolver: object = None, vault_type: VaultType = VaultType.AZURE_INFRASTRUCTURE):
    """
    Obtém a connection string do Azure Blob Storage usando o secret_manager já instanciado.
    O nome do secret é construído como 'azure-storage-connection-string-{grupo}-{empresa}',
    onde grupo é obtido via group_resolver.get_group_for_user(user_email) e empresa via UserEmailParser.parse_email(user_email).
    """
    secret_base_name = 'azure-storage-connection-string'
    if not user_email:
        raise ValueError("user_email é obrigatório para buscar a connection string do Blob Storage.")
    try:
        if group_resolver is not None:
            grupo = group_resolver.get_group_for_user(user_email)
            _, empresa = UserEmailParser.parse_email(user_email)
            secret_name = f"{secret_base_name}-{grupo}-{empresa}"
            connection_string = secret_manager.get_secret(secret_name)
        else:
            usuario, empresa = UserEmailParser.parse_email(user_email)
            secret_name = f"{secret_base_name}-{usuario}-{empresa}"
            connection_string = secret_manager.get_secret(secret_name)
        if not connection_string:
            raise ValueError(f"Connection string '{secret_name}' não encontrada para o usuário '{user_email}' no Key Vault de Blob Storage (infraestrutura Azure).")
        return connection_string
    except Exception as e:
        print(f"[get_blob_connection_string] Erro ao buscar connection string para usuário '{user_email}': {e}")
        raise
