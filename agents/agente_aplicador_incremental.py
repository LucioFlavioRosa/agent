import json
import time
from typing import Dict, Any, Optional
from domain.models.incremental_change_models import CodeTask, TaskExecutionContext, TaskExecutionResult

class AgenteAplicadorIncremental:
    def __init__(self, repository_reader, llm_provider, context_cache_service):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider
        self.context_cache_service = context_cache_service

    def apply_single_task(self, task: CodeTask, context: TaskExecutionContext, job_id: str) -> TaskExecutionResult:
        max_attempts = 3
        attempt = 0
        last_error = None
        while attempt < max_attempts:
            try:
                prompt = self._build_prompt(task, context)
                response = self.llm_provider.executar_prompt(
                    tipo_tarefa="aplicacao_incremental_mudanca",
                    prompt_principal=prompt,
                    max_token_out=8000
                )
                arquivos_modificados = response.get("arquivos_modificados", {})
                success = bool(arquivos_modificados)
                tokens_used = response.get("tokens_saida", 0)
                return TaskExecutionResult(
                    task_id=task.id,
                    success=success,
                    modified_files=arquivos_modificados,
                    error_message=None if success else "LLM returned no modified files",
                    tokens_used=tokens_used
                )
            except Exception as e:
                last_error = str(e)
                attempt += 1
                print(f"[{job_id}] Tentativa {attempt}/{max_attempts} para tarefa {task.id} falhou: {last_error}. Retrying...")
                time.sleep(2 ** (attempt - 1))
        return TaskExecutionResult(
            task_id=task.id,
            success=False,
            modified_files={},
            error_message=last_error,
            tokens_used=0
        )

    def _build_prompt(self, task: CodeTask, context: TaskExecutionContext) -> str:
        related_files_content = ""
        for path, content in context.related_files.items():
            related_files_content += f"\n---\nArquivo: {path}\n{content}\n"
        previous_results_str = json.dumps(context.previous_task_results, indent=2, ensure_ascii=False)
        prompt = f"# PROMPT: APLICADOR INCREMENTAL DE MUDANÇA DE CÓDIGO\n\n## DESCRIÇÃO DA MUDANÇA\n{task.description}\n\n## ARQUIVO ALVO\nCaminho: {task.file_path}\nConteúdo Atual:\n\n{context.related_files.get(task.file_path, '')}\n\n## ARQUIVOS RELACIONADOS (para contexto)\n{related_files_content}\n\n## RESULTADOS DE TAREFAS ANTERIORES\n{previous_results_str}\n\n## FORMATO DE SAÍDA\nRetorne um JSON com a chave 'arquivos_modificados' contendo um dicionário onde a chave é o caminho do arquivo e o valor é o conteúdo completo do arquivo após a mudança."
        return prompt
