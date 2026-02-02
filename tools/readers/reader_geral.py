from typing import Optional

class ReaderGeral:
    def __init__(self, repository_provider, cache_service=None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service

    def read_file(self, repository_type: str, repo_name: str, branch_name: str, file_path: str) -> Optional[str]:
        """
        Lê um arquivo específico do repositório.
        """
        try:
            return self.repository_provider.read_file(repo_name, branch_name, file_path)
        except Exception:
            return None

    def validate_repository_access(self, repository_type: str, repo_name: str, branch_name: str) -> bool:
        """
        Tenta ler o arquivo README.md do repositório para validar acesso antes da análise.
        Retorna True se bem-sucedido, False caso contrário.
        """
        try:
            content = self.read_file(repository_type, repo_name, branch_name, "README.md")
            if content is not None:
                return True
            return False
        except Exception:
            return False
