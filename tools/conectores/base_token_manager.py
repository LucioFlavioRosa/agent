from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.user_email_parser import UserEmailParser

class BaseTokenManager:
    def __init__(self, vault_type: VaultType, group_resolver=None):
        self.vault_type = vault_type
        self.group_resolver = group_resolver
        self.secret_manager = AzureSecretManager(vault_type=vault_type)

    def get_token(self, platform: str, org_name: str, user_email: str) -> str:
        token_secret_name = f"{platform.lower()}-token"
        try:
            token = self.secret_manager.get_secret_with_user_context(token_secret_name, user_email, group_resolver=self.group_resolver)
            return token
        except Exception as e:
            raise ValueError(f"Token '{token_secret_name}' não encontrado para plataforma '{platform}'. Detalhes: {e}") from e
