from typing import List, Optional
from domain.models.rbac_models import User, Token, Repository, BlobContainer

class RBACServiceInterface:
    def authenticate_user(self, jwt_token: str) -> User:
        raise NotImplementedError

    def authorize_repository_access(self, user: User, repo_name: str, repository_type: str) -> bool:
        raise NotImplementedError

    def authorize_blob_access(self, user: User, container_name: str) -> bool:
        raise NotImplementedError

    def get_allowed_tokens_for_user(self, user: User) -> List[Token]:
        raise NotImplementedError

    def get_repository_token(self, user: User, repo_name: str) -> Optional[str]:
        raise NotImplementedError
