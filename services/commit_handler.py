from typing import Dict, Any
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit

class CommitHandler:
    def __init__(self, repository_provider_factory=None, conexao_geral_factory=None):
        self.repository_provider_factory = repository_provider_factory or get_repository_provider_explicit
        self.conexao_geral_factory = conexao_geral_factory or ConexaoGeral.create_with_defaults
    
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                      repository_type: str, repo_name: str) -> None:
        branch_base_para_pr = job_info['data'].get('branch_name', 'main')

        print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")

        repository_provider = self.repository_provider_factory(repository_type)
        conexao_geral = self.conexao_geral_factory()
        repo = conexao_geral.connection(
            repositorio=repo_name,
            repository_type=repository_type,
            repository_provider=repository_provider
        )

        commit_results = []
        for grupo in dados_finais_formatados["grupos"]:
            print(f"[{job_id}] Processando grupo: {grupo.get('titulo_pr', 'Sem título')}")
            
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
            
            print(f"[{job_id}] Resultado do processamento: success={resultado_branch.get('success')}, pr_url={resultado_branch.get('pr_url')}")
            
            if resultado_branch.get('success') and resultado_branch.get('pr_url'):
                print(f"[{job_id}] PR criado com sucesso: {resultado_branch.get('pr_url')}")
            
            commit_results.append(resultado_branch)

        print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
        print(f"[{job_id}] Detalhes dos commits: {[{'success': r.get('success'), 'pr_url': r.get('pr_url'), 'branch': r.get('branch_name')} for r in commit_results]}")
        
        job_info['data']['commit_details'] = commit_results