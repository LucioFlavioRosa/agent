from typing import Dict, List, Any, Literal
from services.commit_handler import CommitHandler
from tools.repository_provider_factory import get_repository_provider_explicit

class IncrementalCommitterService:
    def __init__(self):
        self.commit_handler = CommitHandler()

    def create_incremental_commit(self, job_id: str, task, modified_files: Dict[str, str], repo_name: str, branch_name: str, repository_type: str, commit_strategy: Literal['per_task', 'per_layer', 'single'] = 'per_task') -> Dict[str, Any]:
        print(f"[{job_id}] Usando estratégia de commit: {commit_strategy}")
        pr_url = None
        commit_hash = None
        commit_url = None
        files_committed = list(modified_files.keys())
        if commit_strategy == 'per_task':
            commit_message = f"[Incremental] Step {task.step_number}: {task.action} {task.file_path}\n\n{task.description[:200]}..."
            repository_provider = get_repository_provider_explicit(repository_type)
            commit_result = repository_provider.commit_changes(
                repo_name=repo_name,
                branch_name=branch_name,
                files=modified_files,
                commit_message=commit_message,
                author=None
            )
            commit_hash = commit_result.get('commit_hash')
            commit_url = commit_result.get('commit_url')
            pr_url = commit_result.get('pr_url')
            if not pr_url and hasattr(repository_provider, 'create_pull_request'):
                try:
                    pr_result = repository_provider.create_pull_request(
                        repo_name=repo_name,
                        source_branch=branch_name,
                        target_branch='main',
                        title=commit_message,
                        description=commit_message
                    )
                    pr_url = pr_result.get('pr_url')
                except Exception as e:
                    pr_url = f"ERRO: Falha ao criar PR - {str(e)}"
            return {
                'commit_hash': commit_hash,
                'commit_url': commit_url,
                'pr_url': pr_url,
                'commit_message': commit_message,
                'files_committed': files_committed
            }
        elif commit_strategy == 'per_layer':
            return self.create_grouped_commit(job_id, [task], modified_files, repo_name, branch_name, repository_type, commit_strategy)
        elif commit_strategy == 'single':
            return self.create_grouped_commit(job_id, [task], modified_files, repo_name, branch_name, repository_type, commit_strategy)
        else:
            raise ValueError(f"Estratégia de commit desconhecida: {commit_strategy}")

    def create_grouped_commit(self, job_id: str, tasks: List[Any], modified_files: Dict[str, str], repo_name: str, branch_name: str, repository_type: str, commit_strategy: Literal['per_task', 'per_layer', 'single'] = 'per_layer') -> Dict[str, Any]:
        print(f"[{job_id}] Usando estratégia de commit: {commit_strategy}")
        pr_url = None
        commit_hash = None
        commit_url = None
        if commit_strategy == 'per_layer':
            layer = tasks[0].layer if tasks else 'N/A'
            commit_message = f"[Incremental] Camada {layer}: {len(tasks)} mudanças\n"
            for task in tasks:
                commit_message += f"- Step {task.step_number}: {task.action} {task.file_path}\n"
        elif commit_strategy == 'single':
            commit_message = f"[Incremental] Commit único: {len(tasks)} mudanças\n"
            for task in tasks:
                commit_message += f"- Step {task.step_number}: {task.action} {task.file_path}\n"
        else:
            raise ValueError(f"Estratégia de commit desconhecida: {commit_strategy}")
        repository_provider = get_repository_provider_explicit(repository_type)
        commit_result = repository_provider.commit_changes(
            repo_name=repo_name,
            branch_name=branch_name,
            files=modified_files,
            commit_message=commit_message,
            author=None
        )
        commit_hash = commit_result.get('commit_hash')
        commit_url = commit_result.get('commit_url')
        pr_url = commit_result.get('pr_url')
        if not pr_url and hasattr(repository_provider, 'create_pull_request'):
            try:
                pr_result = repository_provider.create_pull_request(
                    repo_name=repo_name,
                    source_branch=branch_name,
                    target_branch='main',
                    title=commit_message,
                    description=commit_message
                )
                pr_url = pr_result.get('pr_url')
            except Exception as e:
                pr_url = f"ERRO: Falha ao criar PR - {str(e)}"
        return {
            'commit_hash': commit_hash,
            'commit_url': commit_url,
            'pr_url': pr_url,
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
