from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
from domain.models.incremental_change_models import CodeTask, TaskExecutionContext, TaskExecutionResult, TaskDependencyGraph

class IncrementalOrchestratorService:
    def __init__(self, report_parser, dependency_analyzer, context_cache, agente_aplicador, repository_reader, test_runner, committer):
        self.report_parser = report_parser
        self.dependency_analyzer = dependency_analyzer
        self.context_cache = context_cache
        self.agente_aplicador = agente_aplicador
        self.repository_reader = repository_reader
        self.test_runner = test_runner
        self.committer = committer

    def execute_incremental_changes(self, job_id: str, report_text: str, repo_name: str, branch_name: str, repository_type: str) -> Dict[str, Any]:
        tasks = self.report_parser.parse_implementation_plan(report_text)
        codebase = self.repository_reader.read_repository(
            nome_repo=repo_name,
            tipo_analise="incremental_change",
            repository_type=repository_type,
            nome_branch=branch_name
        )
        for file_path, content in codebase.items():
            self.context_cache.cache_file_content(file_path, content)
        graph = self.dependency_analyzer.build_dependency_graph(tasks, codebase)
        levels = self.dependency_analyzer.topological_sort(graph)
        completed_tasks = {}
        execution_order_rationale = []
        for level in levels:
            sorted_tasks = self._sort_tasks_by_priority(level, graph)
            execution_order_rationale.append([task_id for task_id in sorted_tasks])
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_task = {}
                for task_id in sorted_tasks:
                    task = graph.tasks[task_id]
                    context = self._build_task_context(task, completed_tasks)
                    future = executor.submit(self.agente_aplicador.apply_single_task, task, context, job_id)
                    future_to_task[future] = task_id
                for future in as_completed(future_to_task):
                    task_id = future_to_task[future]
                    result = future.result()
                    completed_tasks[task_id] = result
                    if result.success:
                        for file_path, content in result.modified_files.items():
                            self.context_cache.cache_file_content(file_path, content)
                        impacted_files = self.dependency_analyzer.analyze_task_impact(graph.tasks[task_id], codebase)
                        valid = self._validate_task_result(graph.tasks[task_id], result, impacted_files)
                        if valid:
                            self.committer.create_incremental_commit(
                                job_id, graph.tasks[task_id], result.modified_files, repo_name, branch_name, repository_type
                            )
                        else:
                            result.success = False
                            result.error_message = "Test validation failed"
                    else:
                        print(f"[{job_id}] Tarefa {task_id} falhou: {result.error_message}")
        summary = {
            "completed_tasks": [tid for tid, res in completed_tasks.items() if res.success],
            "failed_tasks": [tid for tid, res in completed_tasks.items() if not res.success],
            "commits": [],
            "execution_order_rationale": execution_order_rationale
        }
        return summary

    def _build_task_context(self, task: CodeTask, completed_tasks: Dict[str, TaskExecutionResult]) -> TaskExecutionContext:
        related_files = {}
        related_files[task.file_path] = self.context_cache.get_cached_file(task.file_path) or ""
        for dep in task.dependencies:
            related_files[dep] = self.context_cache.get_cached_file(dep) or ""
        previous_task_results = [res for tid, res in completed_tasks.items() if tid in task.dependencies]
        return TaskExecutionContext(
            task=task,
            related_files=related_files,
            previous_task_results=previous_task_results
        )

    def _validate_task_result(self, task: CodeTask, result: TaskExecutionResult, impacted_files: List[str]) -> bool:
        if not result.success:
            return False
        test_result = self.test_runner.run_tests_for_files(list(result.modified_files.keys()) + impacted_files, "./")
        return test_result.get("success", False)

    def _sort_tasks_by_priority(self, level: List[str], graph: TaskDependencyGraph) -> List[str]:
        def priority(task_id):
            task = graph.tasks[task_id]
            criticidade = sum([1 for t in graph.tasks.values() if task_id in t.dependencies])
            complexidade = task.estimated_tokens
            risco = len(task.dependencies)
            return (-criticidade, -complexidade, -risco)
        return sorted(level, key=priority)
