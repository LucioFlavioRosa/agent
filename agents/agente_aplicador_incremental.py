from domain.models.incremental_change_models import TaskExecutionResult
import os

class AgenteAplicadorIncremental:
    def apply_single_task(self, task, context, job_id):
        if task.action == 'DELETE':
            file_path = task.file_path
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    return TaskExecutionResult(
                        task_id=task.id,
                        success=True,
                        modified_files={},
                        deleted_files=[file_path]
                    )
                except Exception:
                    return TaskExecutionResult(
                        task_id=task.id,
                        success=False,
                        modified_files={},
                        deleted_files=[],
                        error_message=f"Falha ao excluir {file_path}"
                    )
            else:
                return TaskExecutionResult(
                    task_id=task.id,
                    success=True,
                    modified_files={},
                    deleted_files=[]
                )
        # Lógica padrão para criar/modificar arquivos
        # ...
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            modified_files={task.file_path: "conteudo_modificado"},
            deleted_files=[]
        )
