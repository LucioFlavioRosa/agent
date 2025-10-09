from typing import Dict, List, Any, Literal
from services.commit_handler import CommitHandler
from tools.repository_provider_factory import get_repository_provider_explicit
from tools.utils.retry_helper import retry_with_backoff
import logging

def _is_conflict_exception(e):
    return 'TF401028' in str(e) or 'GitReferenceStaleException' in str(e)

class IncrementalCommitterService:
    def __init__(self):
        self.commit_handler = CommitHandler()

    def create_incremental_commit(self, job_id: str, task, modified_files: Dict[str, str], repo_name: str, branch_name: str, repository_type: str, commit_strategy: Literal['per_task', 'per_layer', 'single'] = 'per_task') -> Dict[str, Any]:
        print(f"[{job_id}] Usando estratégia de commit: {commit_strategy}")
        pr_url = None
        commit_hash = None
        commit_url = None
        files_committed = list(modified_files.keys())
        def commit_func():
            commit_message = f"[Incremental] Step {task.step_number}: {task.action} {task.file_path}\n\n{task.description[:200]}..."
            repository_provider = get_repository_provider_explicit(repository_type)
            return repository_provider.commit_changes(
                repo_name=repo_name,
                branch_name=branch_name,
                files=modified_files,
                commit_message=commit_message,
                author=None
            )
        try:
            commit_result = retry_with_backoff(commit_func, max_attempts=3, initial_delay=2, backoff_factor=2, exceptions=(Exception,), job_id=job_id, context_msg='commit_changes')
            commit_hash = commit_result.get('commit_hash')
            commit_url = commit_result.get('commit_url')
            pr_url = commit_result.get('pr_url')
            if not pr_url and hasattr(get_repository_provider_explicit(repository_type), 'create_pull_request'):
                try:
                    pr_result = get_repository_provider_explicit(repository_type).create_pull_request(
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
        except Exception as e:
            if _is_conflict_exception(e):
                logging.warning(f"[{job_id}] [INCREMENTAL_COMMITTER] Conflito de referência ao commitar: {e}")
                return {
                    'commit_hash': None,
                    'commit_url': None,
                    'pr_url': f"ERRO: Conflito de referência ao commitar: {str(e)}",
                    'commit_message': None,
                    'files_committed': []
                }
            logging.error(f"[{job_id}] [INCREMENTAL_COMMITTER] Erro ao commitar: {e}")
            return {
                'commit_hash': None,
                'commit_url': None,
                'pr_url': f"ERRO: Falha ao commitar: {str(e)}",
                'commit_message': None,
                'files_committed': []
            }

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
        def commit_func():
            repository_provider = get_repository_provider_explicit(repository_type)
            return repository_provider.commit_changes(
                repo_name=repo_name,
                branch_name=branch_name,
                files=modified_files,
                commit_message=commit_message,
                author=None
            )
        try:
            commit_result = retry_with_backoff(commit_func, max_attempts=3, initial_delay=2, backoff_factor=2, exceptions=(Exception,), job_id=job_id, context_msg='commit_changes')
            commit_hash = commit_result.get('commit_hash')
            commit_url = commit_result.get('commit_url')
            pr_url = commit_result.get('pr_url')
            if not pr_url and hasattr(get_repository_provider_explicit(repository_type), 'create_pull_request'):
                try:
                    pr_result = get_repository_provider_explicit(repository_type).create_pull_request(
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
        except Exception as e:
            if _is_conflict_exception(e):
                logging.warning(f"[{job_id}] [INCREMENTAL_COMMITTER] Conflito de referência ao commitar: {e}")
                return {
                    'commit_hash': None,
                    'commit_url': None,
                    'pr_url': f"ERRO: Conflito de referência ao commitar: {str(e)}",
                    'commit_message': None,
                    'files_committed': []
                }
            logging.error(f"[{job_id}] [INCREMENTAL_COMMITTER] Erro ao commitar: {e}")
            return {
                'commit_hash': None,
                'commit_url': None,
                'pr_url': f"ERRO: Falha ao commitar: {str(e)}",
                'commit_message': None,
                'files_committed': []
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
