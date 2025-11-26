import os

class AzureSecretManager:
    def __init__(self):
        pass
    def get_secret(self, secret_name: str) -> str:
        return os.environ.get(secret_name, "")
