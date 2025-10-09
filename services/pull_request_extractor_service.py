from typing import List, Dict, Any
from models import PullRequestSummary

class PullRequestExtractorService:
    def extract_pull_requests(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        if job_data.get('aplicar_mudancas_incrementalmente', False):
            print(f"[{job_id}] [PRExtractor] Modo incremental detectado. Extraindo PRs de incremental_execution_summary.")
            return self._extract_prs_from_incremental_summary(job_id, job_data)
        print(f"[{job_id}] [PRExtractor] Modo padrão detectado. Extraindo PRs de commit_details.")
        return self._extract_prs_from_commit_details(job_id, job_data)

    def _extract_prs_from_incremental_summary(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        summary_list = []
        incremental_summary = job_data.get('incremental_execution_summary', {})
        pull_requests = incremental_summary.get('pull_requests', [])
        print(f"[{job_id}] [PRExtractor] Extraindo PRs do modo incremental. Total encontrado: {len(pull_requests)}")
        for pr in pull_requests:
            pr_url = pr.get('pr_url')
            branch_name = pr.get('branch_name', 'branch-desconhecida')
            if not pr_url or not isinstance(pr_url, str) or pr_url.strip() == '':
                print(f"[{job_id}] [PRExtractor] WARNING: PR incremental sem URL válida para branch {branch_name}. Pulando.")
                continue
            task_ids = pr.get('task_ids', [])
            arquivos_modificados = [f"task-{tid}" for tid in task_ids]
            summary_list.append(PullRequestSummary(
                pull_request_url=pr_url,
                branch_name=branch_name,
                arquivos_modificados=arquivos_modificados
            ))
            print(f"[{job_id}] [PRExtractor] PR incremental extraído: branch={branch_name}, url={pr_url}")
        return summary_list

    def _extract_prs_from_commit_details(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        summary_list = []
        commit_details = job_data.get('commit_details', [])
        for pr in commit_details:
            pr_url = pr.get('pr_url')
            branch_name = pr.get('branch_name', 'branch-desconhecida')
            if not pr_url or not isinstance(pr_url, str) or pr_url.strip() == '':
                print(f"[{job_id}] [PRExtractor] WARNING: PR padrão sem URL válida para branch {branch_name}. Pulando.")
                continue
            arquivos_modificados = pr.get('arquivos_modificados', [])
            summary_list.append(PullRequestSummary(
                pull_request_url=pr_url,
                branch_name=branch_name,
                arquivos_modificados=arquivos_modificados
            ))
            print(f"[{job_id}] [PRExtractor] PR padrão extraído: branch={branch_name}, url={pr_url}")
        return summary_list
