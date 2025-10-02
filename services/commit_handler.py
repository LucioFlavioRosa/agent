from typing import Dict, Any
from tools.repo_committers.orchestrator import processar_branch_por_provedor

class CommitHandler:
    def __init__(self):
        pass

    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], repository_type: str, repo_name: str):
        commit_details = []
        branches = dados_finais_formatados.get('branches', [])
        modo_adicao_incremental = job_info.get('data', {}).get('modo_adicao_incremental', False)
        for branch in branches:
            nome_branch = branch.get('nome_branch')
            branch_de_origem = branch.get('branch_de_origem')
            branch_alvo_do_pr = branch.get('branch_alvo_do_pr')
            mensagem_pr = branch.get('mensagem_pr')
            descricao_pr = branch.get('descricao_pr')
            conjunto_de_mudancas = branch.get('conjunto_de_mudancas', [])
            resultado = processar_branch_por_provedor(
                job_info.get('repo_obj'),
                nome_branch,
                branch_de_origem,
                branch_alvo_do_pr,
                mensagem_pr,
                descricao_pr,
                conjunto_de_mudancas,
                repository_type,
                modo_adicao_incremental=modo_adicao_incremental
            )
            commit_details.append(resultado)
        job_info['data']['commit_details'] = commit_details
