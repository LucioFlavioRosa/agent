import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List
from domain.models.incremental_change_models import CodeTask, TaskExecutionResult, TaskExecutionContext

class IncrementalOrchestratorService:
    def __init__(self, report_parser, dependency_analyzer, context_cache, agente_aplicador, repository_reader, test_runner, committer, redis_client):
        self.report_parser = report_parser
        self.dependency_analyzer = dependency_analyzer
        self.context_cache = context_cache
        self.agente_aplicador = agente_aplicador
        self.repository_reader = repository_reader
        self.test_runner = test_runner
        self.committer = committer
        self.redis_client = redis_client

    def execute_incremental_changes(self, job_id: str, report_text: str, repo_name: str, branch_name: str, repository_type: str, completed_task_ids: Optional[List[str]] = None, pause_on_high_impact: bool = False) -> Dict[str, Any]:
        tasks = self.report_parser.parse_implementation_plan(report_text)
        codebase = self.repository_reader.read_repository(repo_name, branch_name, repository_type)
        for file_path, content in codebase.items():
            self.context_cache.cache_file_content(file_path, content)
        graph = self.dependency_analyzer.build_dependency_graph(tasks, codebase)
        levels = self.dependency_analyzer.topological_sort(graph)
        all_tasks = {task.id: task for task in tasks}
        completed_tasks = {}
        failed_tasks = {}
        checkpoint_key = f"checkpoint:{job_id}"
        if completed_task_ids:
            for tid in completed_task_ids:
                result_data = self.context_cache.get_cached_task_context(tid)
                if result_data:
                    completed_tasks[tid] = result_data
        high_impact_tasks = []
        paused_for_high_impact = False
        for level in levels:
            futures = {}
            sorted_level = list(level)
            for tid in sorted_level:
                if tid in completed_tasks or tid in failed_tasks:
                    continue
                task = all_tasks[tid]
                impacted_files = self.dependency_analyzer.analyze_task_impact(task, codebase)
                if impacted_files and len(impacted_files) > 10:
                    print(f"[{job_id}] WARNING: Tarefa {task.id} pode impactar {len(impacted_files)} arquivos. Considere revisão manual.")
                    high_impact_tasks.append(task.id)
                    if pause_on_high_impact:
                        print(f"[{job_id}] PAUSANDO execução incremental antes da tarefa de alto impacto {task.id}.")
                        paused_for_high_impact = True
                        break
            if paused_for_high_impact:
                break
            with ThreadPoolExecutor(max_workers=3) as executor:
                for tid in sorted_level:
                    if tid in completed_tasks or tid in failed_tasks:
                        continue
                    task = all_tasks[tid]
                    context = self._build_task_context(task, completed_tasks)
                    future = executor.submit(self.agente_aplicador.apply_single_task, task, context, job_id)
                    futures[future] = tid
                for future in as_completed(futures):
                    tid = futures[future]
                    try:
                        result = future.result()
                        self.context_cache.cache_task_context(tid, result)
                        if result.success:
                            completed_tasks[tid] = result
                            impacted_files = self.dependency_analyzer.analyze_task_impact(all_tasks[tid], codebase)
                            valid = self._validate_task_result(all_tasks[tid], result, impacted_files)
                            if valid:
                                self.committer.create_incremental_commit(job_id, all_tasks[tid], result.modified_files, repo_name, branch_name, repository_type)
                            else:
                                failed_tasks[tid] = result
                        else:
                            failed_tasks[tid] = result
                    except Exception as e:
                        failed_tasks[tid] = str(e)
            checkpoint_data = {
                "completed_tasks": list(completed_tasks.keys()),
                "failed_tasks": list(failed_tasks.keys())
            }
            self.redis_client.set(checkpoint_key, json.dumps(checkpoint_data))
            print(f"[{job_id}] Checkpoint salvo: {len(completed_tasks)}/{len(all_tasks)} tarefas completadas")
        resumable = len(completed_tasks) < len(all_tasks)
        result_summary = {
            "completed_tasks": list(completed_tasks.keys()),
            "failed_tasks": list(failed_tasks.keys()),
            "commits": [],
            "resumable": resumable,
            "high_impact_tasks": high_impact_tasks
        }
        if high_impact_tasks:
            print(f"[{job_id}] Tarefas de alto impacto detectadas: {high_impact_tasks}")
        if paused_for_high_impact:
            result_summary["paused_for_high_impact"] = True
        return result_summary

    def _build_task_context(self, task: CodeTask, completed_tasks: Dict[str, TaskExecutionResult]) -> TaskExecutionContext:
        related_files = {}
        for dep in task.dependencies:
            cached = self.context_cache.get_cached_file(dep)
            if cached:
                related_files[dep] = cached
        previous_task_results = [completed_tasks[dep].__dict__ for dep in task.dependencies if dep in completed_tasks]
        return TaskExecutionContext(task=task, related_files=related_files, previous_task_results=previous_task_results)

    def _validate_task_result(self, task: CodeTask, result: TaskExecutionResult, impacted_files: List[str]) -> bool:
        test_result = self.test_runner.run_tests_for_files(list(result.modified_files.keys()), "./repo")
        return test_result.get("success", False)

    def get_checkpoint(self, job_id: str) -> Optional[Dict[str, Any]]:
        checkpoint_key = f"checkpoint:{job_id}"
        data = self.redis_client.get(checkpoint_key)
        if data:
            return json.loads(data)
        return None
