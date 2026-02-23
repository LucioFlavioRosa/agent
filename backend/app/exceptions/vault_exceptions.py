class VaultSecretNotFoundError(Exception):
    """
    Exceção lançada quando um segredo não é encontrado no cofre após tentativas com company_id e group_id.
    """
    def __init__(self, key_name: str, vault_type: str):
        self.key_name = key_name
        self.vault_type = vault_type
        message = (
            f"Segredo '{key_name}' não encontrado no cofre '{vault_type}' após tentativas com company_id e group_id."
        )
        super().__init__(message)
