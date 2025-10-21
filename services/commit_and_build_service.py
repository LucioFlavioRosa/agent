class CommitAndBuildService:
    def __init__(self, commit_handler, data_formatter, dotnet_build_service=None):
        self.commit_handler = commit_handler
        self.data_formatter = data_formatter
        self.dotnet_build_service = dotnet_build_service

    def execute_commits_and_builds(self, job_id, job_info, final_result, repository_type, repo_name):
        dados_finais_formatados = self.data_formatter.format_incremental_result_for_commit(final_result)
        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
        if job_info['data'].get('executar_build_dotnet', False) and self.dotnet_build_service:
            commit_details = job_info['data'].get('commit_details', [])
            build_errors = []
            for idx, commit in enumerate(commit_details):
                if 'build_result' not in commit:
                    continue
                if 'build_errors' not in commit:
                    continue
                errors = commit.get('build_errors')
                if errors:
                    build_errors.extend(errors)
            job_info['data']['build_errors'] = build_errors if build_errors else None
