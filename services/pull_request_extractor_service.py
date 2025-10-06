from typing import List, Dict, Any
from models import JobFields, PullRequestSummary

class PullRequestExtractorService:
    """Serviço responsável por extrair informações de Pull Requests dos dados do job."""
    
    def extract_pull_requests(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        """Extrai lista de PRs dos dados do job."""
        summary_list = []
        
        # Primeira tentativa: extrair de commit_details
        summary_list = self._extract_from_commit_details(job_id, job_data)
        
        # Segunda tentativa: extrair de diagnostic_logs se não encontrou PRs
        if not summary_list:
            summary_list = self._extract_from_diagnostic_logs(job_id, job_data)
        
        return summary_list
    
    def _extract_from_commit_details(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        """Extrai PRs dos detalhes de commit."""
        summary_list = []
        commit_details = job_data.get(JobFields.COMMIT_DETAILS, [])
        
        print(f"[{job_id}] Extraindo PRs de commit_details: {len(commit_details)} itens")
        
        for i, pr_info in enumerate(commit_details):
            if not isinstance(pr_info, dict):
                continue
                
            pr_url = pr_info.get('pr_url')
            branch_name = pr_info.get('branch_name')
            arquivos_modificados = pr_info.get('arquivos_modificados', [])
            success = pr_info.get('success', False)
            
            if success and branch_name:
                if pr_url:
                    print(f"[{job_id}] PR válido encontrado: {pr_url} - Branch: {branch_name}")
                    summary_list.append(
                        PullRequestSummary(
                            pull_request_url=pr_url,
                            branch_name=branch_name,
                            arquivos_modificados=arquivos_modificados
                        )
                    )
                else:
                    print(f"[{job_id}] Branch processada sem PR URL: {branch_name}")
                    summary_list.append(
                        PullRequestSummary(
                            pull_request_url=f"Branch processada: {branch_name}",
                            branch_name=branch_name,
                            arquivos_modificados=arquivos_modificados
                        )
                    )
            elif pr_info.get('message') and branch_name:
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_info.get('message', f"Branch processada: {branch_name}"),
                        branch_name=branch_name,
                        arquivos_modificados=arquivos_modificados
                    )
                )
        
        return summary_list
    
    def _extract_from_diagnostic_logs(self, job_id: str, job_data: dict) -> List[PullRequestSummary]:
        """Extrai PRs dos logs de diagnóstico quando commit_details está vazio."""
        summary_list = []
        diagnostic_logs = job_data.get(JobFields.DIAGNOSTIC_LOGS, {})
        
        print(f"[{job_id}] Extraindo PRs de diagnostic_logs")
        
        # Tenta extrair de final_result
        final_result = diagnostic_logs.get('final_result', {})
        if final_result:
            summary_list = self._extract_from_final_result(job_id, final_result)
        
        # Se ainda não encontrou, tenta penultimate_result
        if not summary_list:
            penultimate_result = diagnostic_logs.get('penultimate_result', {})
            if penultimate_result and isinstance(penultimate_result, dict):
                summary_list = self._extract_from_penultimate_result(job_id, penultimate_result)
        
        return summary_list
    
    def _extract_from_final_result(self, job_id: str, final_result: dict) -> List[PullRequestSummary]:
        """Extrai PRs do resultado final dos logs."""
        summary_list = []
        
        for key, value in final_result.items():
            if key.startswith('pr_grupo_') and isinstance(value, dict):
                print(f"[{job_id}] Encontrado grupo de PR: {key}")
                branch_name = value.get('resumo_do_pr', key.replace('pr_grupo_', 'branch-'))
                arquivos_modificados = []
                
                conjunto_mudancas = value.get('conjunto_de_mudancas', [])
                for mudanca in conjunto_mudancas:
                    if mudanca.get('caminho_do_arquivo'):
                        arquivos_modificados.append(mudanca['caminho_do_arquivo'])
                
                pr_url = f"PR criado para branch: {branch_name}"
                
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_url,
                        branch_name=branch_name,
                        arquivos_modificados=arquivos_modificados
                    )
                )
        
        return summary_list
    
    def _extract_from_penultimate_result(self, job_id: str, penultimate_result: dict) -> List[PullRequestSummary]:
        """Extrai PRs do penúltimo resultado dos logs."""
        summary_list = []
        conjunto_mudancas = penultimate_result.get('conjunto_de_mudancas', [])
        
        if conjunto_mudancas:
            arquivos_modificados = []
            for mudanca in conjunto_mudancas:
                if mudanca.get('caminho_do_arquivo'):
                    arquivos_modificados.append(mudanca['caminho_do_arquivo'])
            
            if arquivos_modificados:
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url="PR criado com base no resultado da análise",
                        branch_name="branch-implementacao",
                        arquivos_modificados=arquivos_modificados
                    )
                )
        
        return summary_list
