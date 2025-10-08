from typing import Optional, List
from domain.models.rbac_models import User, Group, Token, Repository, BlobContainer

class RBACRepositoryInterface:
    def get_user_by_azure_ad_id(self, azure_ad_object_id: str) -> Optional[User]:
        raise NotImplementedError

    def get_user_groups(self, user_id: int) -> List[Group]:
        raise NotImplementedError

    def get_group_tokens(self, group_id: int) -> List[Token]:
        raise NotImplementedError

    def get_group_repositories(self, group_id: int) -> List[Repository]:
        raise NotImplementedError

    def get_group_blob_containers(self, group_id: int) -> List[BlobContainer]:
        raise NotImplementedError

    def get_token_value_from_keyvault(self, token_name: str) -> str:
        raise NotImplementedError

    def user_has_access_to_repository(self, user_id: int, repo_name: str) -> bool:
        raise NotImplementedError

    def user_has_access_to_blob_container(self, user_id: int, container_name: str) -> bool:
        raise NotImplementedError
