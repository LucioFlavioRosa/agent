from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.conectores.base_conector import BaseConector

class GitLabConector(BaseConector):
    def _is_gitlab_project_id(self, repositorio: str) -> bool:
        try:
            int(repositorio)
            return True
        except ValueError:
            return False

    def _extract_org_name(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            print(f"[GitLab Conector] GitLab Project ID detectado: {repositorio}. Usando 'gitlab' como org_name para busca de token.")
            return 'gitlab'
        else:
            print(f"[GitLab Conector] GitLab path detectado: {repositorio}. Extraindo namespace para busca de token.")
            try:
                parts = repositorio.strip().split('/')
                if len(parts) >= 2:
                    namespace = parts[0]
                    print(f"[GitLab Conector] Namespace GitLab extraído: {namespace}")
                    return namespace
                else:
                    print(f"[GitLab Conector] Path GitLab inválido. Usando 'gitlab' como fallback.")
                    return 'gitlab'
            except (ValueError, IndexError):
                print(f"[GitLab Conector] Erro ao extrair namespace do path GitLab. Usando 'gitlab' como fallback.")
                return 'gitlab'

    def _normalize_repository_identifier(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            normalized = str(repositorio).strip()
            print(f"[GitLab Conector] GitLab Project ID normalizado: {normalized}")
            return normalized
        else:
            normalized = repositorio.strip()
            print(f"[GitLab Conector] GitLab path normalizado: {normalized}")
            return normalized

    def _extract_user_and_company(self, user_email: str) -> str:
        try:
            local_part = user_email.split('@')[0]
            return local_part
        except Exception:
            raise ValueError(f"Email do usuário inválido para extração: {user_email}")

    def _get_token_for_org(self, org_name: str, platform: str, user_email: str) -> str:
        print(f"[{platform} Conector] Buscando token para organização: {org_name} e usuário: {user_email}")
        user_company = self._extract_user_and_company(user_email)
        token_secret_name = f"{platform.lower()}-{user_company}"
        print(f"[{platform} Conector] Tentando buscar token específico: {token_secret_name}")
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[{platform} Conector] Token específico encontrado para {user_company}")
            return token
        except Exception as e:
            print(f"[{platform} Conector] ERRO CRÍTICO: Token '{token_secret_name}' não encontrado. Não há fallback.")
            raise ValueError(f"ERRO CRÍTICO: Nenhum token {platform} encontrado para '{token_secret_name}'. Verifique se existe no gerenciador de segredos.") from e

    def connection(self, repositorio: str, user_email: str) -> Union[object]:
        normalized_repo = self._normalize_repository_identifier(repositorio)
        org_name = self._extract_org_name(normalized_repo)
        return self._handle_repository_connection(normalized_repo, "GitLab", org_name, user_email)

    def _handle_repository_connection(self, repositorio: str, platform: str, org_name: str, user_email: str) -> Union[object]:
        print(f"[{platform} Conector] Iniciando conexão para repositório {platform}: {repositorio}")
        print(f"[{platform} Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        normalized_repo = repositorio.strip()
        cache_key = f"{platform.lower()}:{normalized_repo}:{user_email}"
        if cache_key in self._cached_repos:
            print(f"[{platform} Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        token = self._get_token_for_org(org_name, platform, user_email)
        masked_token = self._TOKEN_MASK + token[-4:] if len(token) > 4 else self._TOKEN_MASK
        print(f"[{platform} Conector] Token obtido: {masked_token}")
        try:
            print(f"[{platform} Conector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[{platform} Conector] Repositório '{normalized_repo}' encontrado com sucesso.")
        except ValueError as get_error:
            print(f"[{platform} Conector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            print(f"[{platform} Conector] Tentando criar repositório '{normalized_repo}'...")
            try:
                repo = self.repository_provider.create_repository(normalized_repo, token)
                print(f"[{platform} Conector] SUCESSO: Repositório '{normalized_repo}' criado.")
            except Exception as create_error:
                print(f"[{platform} Conector] ERRO: Falha ao criar repositório '{normalized_repo}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        except Exception as unexpected_error:
            print(f"[{platform} Conector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        print(f"[{platform} Conector] Adicionando repositório '{normalized_repo}' ao cache com chave '{cache_key}'.")
        self._cached_repos[cache_key] = repo
        return repo

    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        return cls(repository_provider=GitLabRepositoryProvider())
