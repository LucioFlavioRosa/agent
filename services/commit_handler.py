class CommitHandler:
    def __init__(self, committer=None):
        self.committer = committer

    def execute_commits(self, job_id, job_info, dados_finais_formatados, repository_type, repo_name):
        if not hasattr(self, 'committer') or self.committer is None:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: CommitHandler.committer não foi inicializado corretamente. Tipo: {type(getattr(self, 'committer', None))}")
        print(f"[{job_id}] [CommitHandler] Tipo do committer: {type(self.committer)}, Métodos disponíveis: {dir(self.committer)[:5]}...")
        commit_results = []
        for idx, grupo in enumerate(dados_finais_formatados):
            pr_url = None
            try:
                pr_url = self.committer.criar_branch(repo_name, grupo['branch_name'], repository_type)
                pr_url = self.committer.criar_pull_request(repo_name, grupo['branch_name'], grupo['arquivos_modificados'], repository_type)
                commit_results.append({
                    'branch_name': grupo['branch_name'],
                    'success': True,
                    'pr_url': pr_url,
                    'message': 'PR criado com sucesso',
                    'arquivos_modificados': grupo['arquivos_modificados']
                })
            except Exception as e:
                commit_results.append({
                    'branch_name': grupo['branch_name'],
                    'success': False,
                    'pr_url': f'ERRO: {str(e)}',
                    'message': str(e),
                    'arquivos_modificados': []
                })
        job_info['data']['commit_details'] = commit_results
        print(f"[{job_id}] DIAGNÓSTICO FINAL - commit_results antes de salvar: {commit_results}")
