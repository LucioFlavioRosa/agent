from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.user_email_parser import UserEmailParser

class BaseTokenManager:
    def __init__(self, vault_type: VaultType, group_resolver=None):
        self.vault_type = vault_type
        self.group_resolver = group_resolver
        self.secret_manager = AzureSecretManager(vault_type=vault_type)

    def get_token(self, platform: str, user_email: str) -> str:
        """
        Obtém o token usando o email completo do usuário e o group_resolver.
        O nome do secret é construído como '{platform.lower()}-token-{grupo}-{empresa}',
        onde grupo é obtido via group_resolver.get_group_for_user(user_email) e empresa via UserEmailParser.parse_email(user_email).
        """
        if self.group_resolver is not None:
            grupo = self.group_resolver.get_group_for_user(user_email)
            _, empresa = UserEmailParser.parse_email(user_email)
            token_secret_name = f"{platform.lower()}-token-{grupo}-{empresa}"
        else:
            usuario, empresa = UserEmailParser.parse_email(user_email)
            token_secret_name = f"{platform.lower()}-token-{usuario}-{empresa}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            return token
        except Exception as e:
            raise ValueError(f"Token '{token_secret_name}' não encontrado para plataforma '{platform}'. Detalhes: {e}") from e
