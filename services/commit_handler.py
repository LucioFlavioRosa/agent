from typing import List, Dict, Any
from services.dotnet_build_service import DotNetBuildService

class CommitHandler:
    def __init__(self):
        self.build_service = DotNetBuildService()

    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], repository_type: str, repo_name: str):
        commit_details = job_info['data'].get('commit_details', [])
        for commit_info in commit_details:
            if job_info['data'].get('executar_build_dotnet', False):
                branch_name = commit_info.get('branch_name')
                if not branch_name:
                    raise ValueError(f"[{job_id}] ERRO: branch_name ausente em commit_info para build.")
                access_token = job_info['data'].get('access_token')
                print(f"[{job_id}] [CommitHandler] Iniciando build. repository_type={repository_type}, repo_name={repo_name}, branch_name={branch_name}, access_token presente: {bool(access_token)}")
                build_result = self.build_service.build_project(job_id, repository_type, repo_name, branch_name, access_token)
                print(f"[{job_id}] [CommitHandler] Build finalizado. success={build_result.get('success')}, errors={len(build_result.get('errors', []))}")
                commit_info['build_result'] = build_result
                commit_info['build_errors'] = build_result.get('errors')
