class BranchSourceValidator:
    @staticmethod
    def validate_file_exists_in_branch(repo, file_path: str, branch_name: str, repository_type: str) -> bool:
        if repository_type == 'azure':
            from tools.readers.azure_reader import AzureReader
            reader = AzureReader(repository_provider=None)
        elif repository_type == 'github':
            from tools.readers.github_reader import GitHubReader
            reader = GitHubReader(repository_provider=None)
        elif repository_type == 'gitlab':
            from tools.readers.gitlab_reader import GitLabReader
            reader = GitLabReader(repository_provider=None)
        else:
            return False
        try:
            return reader.file_exists(repo, file_path, branch_name)
        except Exception:
            return False
