from typing import List, Dict, Any
from models import PullRequestSummary

class PullRequestExtractorService:
    def extract_pull_requests(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        aplicar_incremental = job_data.get('aplicar_mudancas_incrementalmente', False)
        print(f"[{job_id}] [PRExtractor] Modo {'incremental' if aplicar_incremental else 'padrão'} detectado. Extraindo PRs.")
        if aplicar_incremental:
            return self._extract_prs_from_incremental_summary(job_id, job_data)
        return self._extract_prs_from_commit_details(job_id, job_data)

    def _validate_pr_url(self, pr_url: str) -> bool:
        if not pr_url or not isinstance(pr_url, str):
            return False
        return (
            pr_url.startswith('http://') or
            pr_url.startswith('https://') or
            'PR criado' in pr_url or
            'Branch processada' in pr_url
        )

    def _extract_prs_from_incremental_summary(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        summary_list = []
        incremental_summary = job_data.get('incremental_execution_summary', {})
        pull_requests = incremental_summary.get('pull_requests', [])
        print(f"[{job_id}] [PRExtractor] Extraindo PRs do modo incremental. Total encontrado: {len(pull_requests)}")
        if not pull_requests:
            commit_details = job_data.get('commit_details', [])
            print(f"[{job_id}] [PRExtractor] FALLBACK: incremental_execution_summary vazio, lendo de commit_details. Total: {len(commit_details)}")
            for pr in commit_details:
                pr_url = pr.get('pr_url')
                branch_name = pr.get('branch_name', 'branch-desconhecida')
                print(f"[{job_id}] [PRExtractor] Validando PR fallback: branch={branch_name}, pr_url='{pr_url}'")
                if not self._validate_pr_url(pr_url):
                    print(f"[{job_id}] [PRExtractor] WARNING: PR fallback REJEITADO para branch {branch_name}. URL: '{pr_url}'")
                    continue
                arquivos_modificados = pr.get('arquivos_modificados', [])
                summary_list.append(PullRequestSummary(
                    pull_request_url=pr_url,
                    branch_name=branch_name,
                    arquivos_modificados=arquivos_modificados
                ))
                print(f"[{job_id}] [PRExtractor] PR fallback ACEITO: branch={branch_name}, url={pr_url}")
            print(f"[{job_id}] [PRExtractor] PRs válidos extraídos (fallback): {len(summary_list)}")
            return summary_list
        for pr in pull_requests:
            pr_url = pr.get('pr_url')
            branch_name = pr.get('branch_name', 'branch-desconhecida')
            print(f"[{job_id}] [PRExtractor] Validando PR incremental: branch={branch_name}, pr_url='{pr_url}'")
            if not self._validate_pr_url(pr_url):
                print(f"[{job_id}] [PRExtractor] WARNING: PR incremental REJEITADO para branch {branch_name}. URL: '{pr_url}'")
                continue
            task_ids = pr.get('task_ids', [])
            arquivos_modificados = [f"task-{tid}" for tid in task_ids]
            summary_list.append(PullRequestSummary(
                pull_request_url=pr_url,
                branch_name=branch_name,
                arquivos_modificados=arquivos_modificados
            ))
            print(f"[{job_id}] [PRExtractor] PR incremental ACEITO: branch={branch_name}, url={pr_url}")
        print(f"[{job_id}] [PRExtractor] PRs válidos extraídos (incremental): {len(summary_list)}")
        return summary_list

    def _extract_prs_from_commit_details(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        summary_list = []
        commit_details = job_data.get('commit_details', [])
        print(f"[{job_id}] [PRExtractor] Extraindo PRs do modo padrão. Total encontrado: {len(commit_details)}")
        for pr in commit_details:
            pr_url = pr.get('pr_url')
            branch_name = pr.get('branch_name', 'branch-desconhecida')
            print(f"[{job_id}] [PRExtractor] Validando PR padrão: branch={branch_name}, pr_url='{pr_url}'")
            if not self._validate_pr_url(pr_url):
                print(f"[{job_id}] [PRExtractor] WARNING: PR padrão REJEITADO para branch {branch_name}. URL: '{pr_url}'")
                continue
            arquivos_modificados = pr.get('arquivos_modificados', [])
            summary_list.append(PullRequestSummary(
                pull_request_url=pr_url,
                branch_name=branch_name,
                arquivos_modificados=arquivos_modificados
            ))
            print(f"[{job_id}] [PRExtractor] PR padrão ACEITO: branch={branch_name}, url={pr_url}")
        print(f"[{job_id}] [PRExtractor] PRs válidos extraídos (padrão): {len(summary_list)}")
        return summary_list
