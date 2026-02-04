from typing import List, Dict, Any
from models import JobFields, PullRequestSummary

class PullRequestExtractorService:
    def extract_pull_requests(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        """
        Extrai pull requests de diferentes fontes do job_data de forma simples e manutenível.
        """
        return self._extract_pull_requests_from_data(job_id, job_data)

    def _extract_pull_requests_from_data(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        summary_list = []
        # Extrai de commit_details
        commit_details = job_data.get('commit_details', [])
        for pr_info in commit_details:
            if not isinstance(pr_info, dict):
                continue
            pr_url = pr_info.get('pr_url')
            branch_name = pr_info.get('branch_name')
            arquivos_modificados = pr_info.get('arquivos_modificados', [])
            build_result = pr_info.get('build_result') if 'build_result' in pr_info else None
            commit_url = pr_info.get('commit_url') if 'commit_url' in pr_info else None
            success = pr_info.get('success', False)
            if success and branch_name:
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_url if pr_url else f"Branch processada: {branch_name}",
                        branch_name=branch_name,
                        arquivos_modificados=arquivos_modificados,
                        build_result=build_result,
                        commit_url=commit_url
                    )
                )
            elif pr_info.get('message') and branch_name:
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_info.get('message', f"Branch processada: {branch_name}"),
                        branch_name=branch_name,
                        arquivos_modificados=arquivos_modificados,
                        build_result=build_result,
                        commit_url=commit_url
                    )
                )
        # Extrai de diagnostic_logs
        diagnostic_logs = job_data.get('diagnostic_logs', {})
        final_result = diagnostic_logs.get('final_result', {})
        penultimate_result = diagnostic_logs.get('penultimate_result', {})
        # Final result (PRs agrupados)
        for key, value in final_result.items():
            if key.startswith('pr_grupo_') and isinstance(value, dict):
                branch_name = value.get('resumo_do_pr', key.replace('pr_grupo_', 'branch-'))
                arquivos_modificados = [mudanca['caminho_do_arquivo'] for mudanca in value.get('conjunto_de_mudancas', []) if mudanca.get('caminho_do_arquivo')]
                pr_url = f"PR criado para branch: {branch_name}"
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_url,
                        branch_name=branch_name,
                        arquivos_modificados=arquivos_modificados,
                        build_result=None,
                        commit_url=None
                    )
                )
        # Penultimate result (PR único)
        if penultimate_result and isinstance(penultimate_result, dict):
            arquivos_modificados = [mudanca['caminho_do_arquivo'] for mudanca in penultimate_result.get('conjunto_de_mudancas', []) if mudanca.get('caminho_do_arquivo')]
            if arquivos_modificados:
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url="PR criado com base no resultado da análise",
                        branch_name="branch-implementacao",
                        arquivos_modificados=arquivos_modificados,
                        build_result=None,
                        commit_url=None
                    )
                )
        return summary_list
