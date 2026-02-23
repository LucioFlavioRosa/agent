class BlobStorageConnectionError(Exception):
    """
    Exceção lançada quando ocorre falha ao obter a connection string do Blob Storage a partir do Vault.
    """
    def __init__(self, company_id: str, vault_type: str, key_name: str, original_exception: Exception = None):
        self.company_id = company_id
        self.vault_type = vault_type
        self.key_name = key_name
        self.original_exception = original_exception
        message = (
            f"Erro ao obter connection string do Blob Storage para company_id '{company_id}' "
            f"no vault '{vault_type}' com chave '{key_name}'."
        )
        if original_exception:
            message += f" Detalhes: {str(original_exception)}"
        super().__init__(message)

class BlobUploadError(Exception):
    """
    Exceção lançada quando ocorre falha ao fazer upload de um documento para o Blob Storage.
    """
    def __init__(self, blob_path: str, filename: str, original_exception: Exception = None):
        self.blob_path = blob_path
        self.filename = filename
        self.original_exception = original_exception
        message = (
            f"Erro ao fazer upload do arquivo '{filename}' para o Blob Storage no caminho '{blob_path}'."
        )
        if original_exception:
            message += f" Detalhes: {str(original_exception)}"
        super().__init__(message)

class BlobContainerError(Exception):
    """
    Exceção lançada quando ocorre falha ao criar ou acessar um container no Blob Storage.
    """
    def __init__(self, container_name: str, original_exception: Exception = None):
        self.container_name = container_name
        self.original_exception = original_exception
        message = (
            f"Erro ao criar ou acessar o container '{container_name}' no Blob Storage."
        )
        if original_exception:
            message += f" Detalhes: {str(original_exception)}"
        super().__init__(message)
