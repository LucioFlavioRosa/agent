from typing import Optional

def _extract_user_and_company_from_email(user_email: str):
    if not user_email or '@' not in user_email:
        raise ValueError("user_email inválido ou não informado")
    local, domain = user_email.split('@', 1)
    usuario = local.replace('.', '_')
    empresa = domain.split('.', 1)[0].replace('.', '_')
    return usuario, empresa

class ReaderGeral:
    def __init__(self, repository_provider, cache_service=None, user_email: Optional[str] = None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service
        self.user_email = user_email
        if user_email:
            self.usuario, self.empresa = _extract_user_and_company_from_email(user_email)
        else:
            self.usuario, self.empresa = None, None

    def read_file(self, repository_type: str, repo_name: str, branch_name: str, file_path: str) -> Optional[str]:
        try:
            if self.user_email:
                return self.repository_provider.read_file(repo_name, branch_name, file_path, usuario=self.usuario, empresa=self.empresa)
            else:
                return self.repository_provider.read_file(repo_name, branch_name, file_path)
        except Exception:
            return None

    def validate_repository_access(self, repository_type: str, repo_name: str, branch_name: str) -> bool:
        try:
            if self.user_email:
                content = self.read_file(repository_type, repo_name, branch_name, "README.md")
            else:
                content = self.read_file(repository_type, repo_name, branch_name, "README.md")
            if content is not None:
                return True
            return False
        except Exception:
            return False
