from typing import Any, Dict, List, Optional
from services.dotnet_build_service import DotNetBuildService
from tools.azure_secret_manager import AzureSecretManager
from models import JobFields

class CommitHandler:
    def __init__(self, secret_manager: Optional[Any] = None):
        self.secret_manager = secret_manager or AzureSecretManager()

    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], repository_type: str, repo_name: str):
        # ... lógica de commit e PR ...
        # Após o commit e PR, se executar_build_dotnet=True, executar build
        executar_build_dotnet = job_info['data'].get('executar_build_dotnet', False)
        if executar_build_dotnet:
            commit_details = job_info['data'].get('commit_details', [])
            for idx, commit in enumerate(commit_details):
                branch_name = commit.get('branch_name')
                repo_name_commit = commit.get('repo_name', repo_name)
                token = self._get_access_token(repository_type, repo_name_commit)
                dotnet_build_service = DotNetBuildService()
                build_result = dotnet_build_service.build_project(job_id, repository_type, repo_name_commit, branch_name, access_token=token)
                commit['build_result'] = build_result
                if not build_result.get('success'):
                    commit['build_errors'] = build_result.get('errors')
            job_info['data']['commit_details'] = commit_details

    def _get_access_token(self, repository_type: str, repo_name: str) -> Optional[str]:
        if repository_type == 'azure':
            parts = repo_name.split('/')
            if len(parts) != 3:
                raise ValueError(f"Nome do repositório '{repo_name}' tem formato inválido para Azure.")
            org_name = parts[0]
            platform = 'Azure'
        elif repository_type == 'github':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitHub'
        elif repository_type == 'gitlab':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitLab'
        else:
            raise ValueError(f"Tipo de repositório '{repository_type}' não suportado para obtenção de token.")
        token_secret_name = f"{platform.lower()}-token-{org_name}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            return token
        except Exception:
            try:
                token = self.secret_manager.get_secret(f"{platform.lower()}-token")
                return token
            except Exception:
                raise ValueError(f"Não foi possível obter token para {platform} ({org_name})")
