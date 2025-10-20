class CommitHandler:
    def execute_commits(self, job_id, job_info, dados_finais_formatados, repository_type, repo_name):
        if job_info['data'].get('gerar_epicos', False) or job_info['data'].get('gerar_tarefas', False):
            print(f"[{job_id}] [CommitHandler] Commit e PR ignorados pois gerar_epicos ou gerar_tarefas está ativo.")
            return
        # ... restante da lógica original de commit ...
        # O restante do código permanece inalterado, incluindo lógica de commit, PR, etc.