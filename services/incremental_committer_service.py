from typing import Dict, List, Any
from services.commit_handler import CommitHandler
from tools.repository_provider_factory import get_repository_provider_explicit

class IncrementalCommitterService:
    def __init__(self):
        self.commit_handler = CommitHandler()

    def create_incremental_commit(self, job_id: str, task, modified_files: Dict[str, str], repo_name: str, branch_name: str, repository_type: str) -> Dict[str, Any]:
        commit_message = f"[Incremental] Step {task.step_number}: {task.action} {task.file_path}\n\n{task.description[:200]}..."
        repository_provider = get_repository_provider_explicit(repository_type)
        commit_result = repository_provider.commit_changes(
            repo_name=repo_name,
            branch_name=branch_name,
            files=modified_files,
            commit_message=commit_message,
            author=None
        )
        return {
            'commit_hash': commit_result.get('commit_hash'),
            'commit_url': commit_result.get('commit_url'),
            'commit_message': commit_message,
            'files_committed': list(modified_files.keys())
        }

    def create_grouped_commit(self, job_id: str, tasks: List[Any], modified_files: Dict[str, str], repo_name: str, branch_name: str, repository_type: str) -> Dict[str, Any]:
        layer = tasks[0].layer if tasks else 'N/A'
        commit_message = f"[Incremental] Camada {layer}: {len(tasks)} mudanças\n"
        for task in tasks:
            commit_message += f"- Step {task.step_number}: {task.action} {task.file_path}\n"
        repository_provider = get_repository_provider_explicit(repository_type)
        commit_result = repository_provider.commit_changes(
            repo_name=repo_name,
            branch_name=branch_name,
            files=modified_files,
            commit_message=commit_message,
            author=None
        )
        return {
            'commit_hash': commit_result.get('commit_hash'),
            'commit_url': commit_result.get('commit_url'),
            'commit_message': commit_message,
            'files_committed': list(modified_files.keys())
        }

    def rollback_commit(self, commit_hash: str, repo_name: str, repository_type: str) -> Dict[str, Any]:
        repository_provider = get_repository_provider_explicit(repository_type)
        try:
            result = repository_provider.revert_commit(
                repo_name=repo_name,
                commit_hash=commit_hash
            )
            return {
                'success': True,
                'details': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
