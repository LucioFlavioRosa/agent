from pydantic import BaseModel
from typing import List, Optional

class Token(BaseModel):
    id: int
    token_name: str
    token_type: str
    created_at: Optional[str]

class Repository(BaseModel):
    id: int
    repo_name: str
    repository_type: str
    token: Optional[Token]
    created_at: Optional[str]

class BlobContainer(BaseModel):
    id: int
    container_name: str
    storage_account_url: str
    created_at: Optional[str]

class Group(BaseModel):
    id: int
    name: str
    description: Optional[str]
    users: Optional[List['User']] = None
    tokens: Optional[List[Token]] = None
    repositories: Optional[List[Repository]] = None
    blob_containers: Optional[List[BlobContainer]] = None
    created_at: Optional[str]

class User(BaseModel):
    id: int
    azure_ad_object_id: str
    email: str
    name: str
    is_active: bool
    groups: Optional[List[Group]] = None
    created_at: Optional[str]

Group.update_forward_refs()
