class SecretNotFoundException(Exception):
    """
    Exceção lançada quando o segredo não é encontrado em nenhum dos padrões de nome definidos.
    """
    def __init__(self, secret_name: str):
        super().__init__(f"Segredo '{secret_name}' não encontrado no Key Vault.")
        self.secret_name = secret_name

class KeyVaultConnectionError(Exception):
    """
    Exceção lançada quando ocorre uma falha na conexão com o Azure Key Vault.
    """
    def __init__(self, vault_url: str, original_exception: Exception = None):
        message = f"Falha ao conectar ao Key Vault em '{vault_url}'."
        if original_exception:
            message += f" Detalhes: {str(original_exception)}"
        super().__init__(message)
        self.vault_url = vault_url
        self.original_exception = original_exception

class InvalidSecretFormatError(Exception):
    """
    Exceção lançada quando o formato do segredo recuperado é inválido ou inesperado.
    """
    def __init__(self, secret_name: str, details: str = ""):
        message = f"Formato inválido para o segredo '{secret_name}'."
        if details:
            message += f" Detalhes: {details}"
        super().__init__(message)
        self.secret_name = secret_name
        self.details = details
