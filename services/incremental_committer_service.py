class IncrementalCommitterService:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider

    def create_incremental_commit(self, job_id, task, modified_files, repo_name, branch_name, repository_type):
        if not hasattr(self, 'repository_provider') or not hasattr(self.repository_provider, 'criar_branch'):
            raise ValueError(f"[{job_id}] ERRO: repository_provider inválido. Tipo: {type(getattr(self, 'repository_provider', None))}, Métodos: {dir(getattr(self, 'repository_provider', None))[:5]}...")
        # Implementação real do commit incremental (mock para exemplo)
        pr_url = f"https://fake-pr-url/{branch_name}/{task.id}"
        return {
            'branch_name': branch_name,
            'pr_url': pr_url,
            'success': True,
            'message': 'PR criado incrementalmente',
            'arquivos_modificados': list(modified_files.keys())
        }
