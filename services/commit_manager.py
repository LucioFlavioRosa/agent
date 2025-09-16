from typing import Dict, Any
from domain.interfaces.commit_manager_interface import ICommitManager
from domain.interfaces.job_manager_interface import IJobManager
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit

class CommitManager(ICommitManager):
    def __init__(self, job_manager: IJobManager):
        self.job_manager = job_manager
    
    def format_final_data(self, dados_preenchidos: Dict[str, Any]) -> Dict[str, Any]:
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}

        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral":
                continue
            dados_finais_formatados["grupos"].append({
                "branch_sugerida": nome_grupo, 
                "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), 
                "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), 
                "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])
            })

        return dados_finais_formatados
    
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                       repository_type: str, repo_name: str) -> None:

        branch_base_para_pr = job_info['data'].get('branch_name', 'main')

        print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")

        repository_provider = get_repository_provider_explicit(repository_type)
        conexao_geral = ConexaoGeral.create_with_defaults()
        repo = conexao_geral.connection(
            repositorio=repo_name,
            repository_type=repository_type,
            repository_provider=repository_provider
        )

        commit_results = []
        for grupo in dados_finais_formatados["grupos"]:
            resultado_branch = processar_branch_por_provedor(
                repo=repo,
                nome_branch=grupo["branch_sugerida"],
                branch_de_origem=branch_base_para_pr,
                branch_alvo_do_pr=branch_base_para_pr,
                mensagem_pr=grupo["titulo_pr"],
                descricao_pr=grupo["resumo_do_pr"],
                conjunto_de_mudancas=grupo["conjunto_de_mudancas"],
                repository_type=repository_type
            )
            commit_results.append(resultado_branch)

        print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
        job_info['data']['commit_details'] = commit_results
        self.job_manager.update_job(job_id, job_info)