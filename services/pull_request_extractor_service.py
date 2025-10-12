from typing import List, Dict, Any, Optional
from models import PullRequestSummary

class PullRequestExtractorService:
    def extract_pull_requests(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        commit_details = job_data.get('commit_details', [])
        summary_list = []
        for commit in commit_details:
            pull_request_url = commit.get('pr_url')
            branch_name = commit.get('branch_name')
            arquivos_modificados = commit.get('arquivos_modificados', [])
            build_result = commit.get('build_result') if 'build_result' in commit else None
            commit_url = commit.get('commit_url') if 'commit_url' in commit else None
            summary = PullRequestSummary(
                pull_request_url=pull_request_url,
                branch_name=branch_name,
                arquivos_modificados=arquivos_modificados,
                build_result=build_result,
                commit_url=commit_url
            )
            summary_list.append(summary)
        return summary_list
