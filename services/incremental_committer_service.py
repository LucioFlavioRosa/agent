class IncrementalCommitterService:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider

    def create_incremental_commit(self, job_id, task, modified_files, repo_name, branch_name, repository_type):
        if not hasattr(self, 'repository_provider') or not hasattr(self.repository_provider, 'criar_branch'):
            raise ValueError(f"[{job_id}] ERRO: repository_provider inválido. Tipo: {type(getattr(self, 'repository_provider', None))}, Métodos: {dir(getattr(self, 'repository_provider', None))[:5]}...")
        branch = self.repository_provider.criar_branch(repo_name, branch_name, repository_type)
        pr_url = self.repository_provider.criar_pull_request(repo_name, branch_name, modified_files, repository_type)
        return {'branch': branch, 'pr_url': pr_url}
