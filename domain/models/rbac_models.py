from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Literal
from datetime import datetime
import uuid

class Token(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do token")
    token_name: str = Field(..., min_length=1, max_length=100, description="Nome identificador do token")
    token_type: Literal['github', 'gitlab', 'azure'] = Field(..., description="Tipo do repositório associado")
    token_value: Optional[str] = Field(None, description="Valor do token (sensível, não expor em logs)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação do token")
    is_active: bool = Field(default=True, description="Indica se o token está ativo")

    @field_validator('token_name')
    @classmethod
    def validate_token_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('token_name não pode ser vazio')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "token_name": "GitHub Token - Projeto X",
                "token_type": "github",
                "created_at": "2024-01-15T10:30:00Z",
                "is_active": True
            }
        }

class Repository(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do repositório")
    repo_name: str = Field(..., min_length=1, description="Nome completo do repositório (ex: owner/repo)")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(..., description="Tipo do repositório")
    token: Token = Field(..., description="Token de acesso associado ao repositório")
    is_active: bool = Field(default=True, description="Indica se o repositório está ativo")

    @field_validator('repo_name')
    @classmethod
    def validate_repo_name(cls, v: str, values) -> str:
        repository_type = values.get('repository_type')
        if repository_type in ['github', 'gitlab'] and '/' not in v:
            raise ValueError('repo_name deve estar no formato owner/repo para GitHub/GitLab')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "repo_name": "empresa/projeto-x",
                "repository_type": "github",
                "token": {"id": "550e8400-e29b-41d4-a716-446655440000", "token_name": "GitHub Token", "token_type": "github"},
                "is_active": True
            }
        }

class BlobContainer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do container")
    container_name: str = Field(..., min_length=3, max_length=63, description="Nome do container no Azure Blob Storage")
    storage_account_url: str = Field(..., description="URL da conta de armazenamento (ex: https://account.blob.core.windows.net)")
    is_active: bool = Field(default=True, description="Indica se o container está ativo")

    @field_validator('container_name')
    @classmethod
    def validate_container_name(cls, v: str) -> str:
        # Azure: lowercase, números, hífens, 3-63 caracteres
        if not v.islower() or not v.replace('-', '').isalnum():
            raise ValueError('container_name deve conter apenas letras minúsculas, números e hífens')
        if not (3 <= len(v) <= 63):
            raise ValueError('container_name deve ter entre 3 e 63 caracteres')
        return v

    @field_validator('storage_account_url')
    @classmethod
    def validate_storage_url(cls, v: str) -> str:
        if not v.startswith('https://'):
            raise ValueError('storage_account_url deve começar com https://')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "container_name": "relatorios-projeto-x",
                "storage_account_url": "https://mystorageaccount.blob.core.windows.net",
                "is_active": True
            }
        }

class Group(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do grupo")
    name: str = Field(..., min_length=1, max_length=100, description="Nome do grupo")
    description: Optional[str] = Field(None, max_length=500, description="Descrição do grupo")
    tokens: List[Token] = Field(default_factory=list, description="Tokens de acesso do grupo")
    repositories: List[Repository] = Field(default_factory=list, description="Repositórios acessíveis pelo grupo")
    blob_containers: List[BlobContainer] = Field(default_factory=list, description="Containers de blob acessíveis")
    is_active: bool = Field(default=True, description="Indica se o grupo está ativo")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação do grupo")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name não pode ser vazio')
        return v.strip()

    def add_token(self, token: Token) -> None:
        if token.id not in [t.id for t in self.tokens]:
            self.tokens.append(token)

    def add_repository(self, repository: Repository) -> None:
        if repository.id not in [r.id for r in self.repositories]:
            self.repositories.append(repository)

    def add_blob_container(self, container: BlobContainer) -> None:
        if container.id not in [c.id for c in self.blob_containers]:
            self.blob_containers.append(container)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "name": "Equipe Backend",
                "description": "Grupo com acesso aos repositórios e recursos do backend",
                "tokens": [],
                "repositories": [],
                "blob_containers": [],
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do usuário")
    azure_ad_object_id: Optional[str] = Field(None, description="Object ID do Azure AD (quando disponível)")
    email: EmailStr = Field(..., description="Email do usuário (validado)")
    name: str = Field(..., min_length=1, max_length=200, description="Nome completo do usuário")
    is_active: bool = Field(default=True, description="Indica se o usuário está ativo")
    groups: List[Group] = Field(default_factory=list, description="Grupos aos quais o usuário pertence")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação do usuário")
    last_login: Optional[datetime] = Field(None, description="Data do último login")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name não pode ser vazio')
        return v.strip()

    def add_to_group(self, group: Group) -> None:
        if group.id not in [g.id for g in self.groups]:
            self.groups.append(group)

    def has_access_to_repository(self, repo_name: str) -> bool:
        for group in self.groups:
            if group.is_active and any(r.repo_name == repo_name and r.is_active for r in group.repositories):
                return True
        return False

    def has_access_to_blob_container(self, container_name: str) -> bool:
        for group in self.groups:
            if group.is_active and any(c.container_name == container_name and c.is_active for c in group.blob_containers):
                return True
        return False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440004",
                "azure_ad_object_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "usuario@empresa.com",
                "name": "João Silva",
                "is_active": True,
                "groups": [],
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-20T14:25:00Z"
            }
        }
