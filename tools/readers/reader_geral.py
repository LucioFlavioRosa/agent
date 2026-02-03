from typing import Optional
from tools.user_email_parser import UserEmailParser

class ReaderGeral:
    def __init__(self, repository_provider, cache_service=None, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service
        self.user_email = user_email
        self.group_resolver = group_resolver
        if user_email:
            # Obtém grupo diretamente do MongoDB usando o e-mail
            grupo = group_resolver.get_group_for_user(user_email) if group_resolver is not None else None
            usuario, empresa = UserEmailParser.parse_email(user_email)
            self.usuario = usuario
            self.empresa = empresa
            self.grupo = grupo
        else:
            self.usuario = None
            self.empresa = None
            self.grupo = None

    def read_file(self, repository_type: str, repo_name: str, branch_name: str, file_path: str) -> Optional[str]:
        try:
            if self.user_email:
                # Passa grupo e empresa ao invés de usuario e empresa
                return self.repository_provider.read_file(repo_name, branch_name, file_path, grupo=self.grupo, empresa=self.empresa)
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
