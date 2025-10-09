import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List
from domain.models.incremental_change_models import CodeTask, TaskExecutionResult, TaskExecutionContext

class IncrementalOrchestratorService:
    def __init__(self, report_parser, dependency_analyzer, context_cache, agente_aplicador, repository_reader, test_runner, committer, redis_client=None):
        self.report_parser = report_parser
        self.dependency_analyzer = dependency_analyzer
        self.context_cache = context_cache
        self.agente_aplicador = agente_aplicador
        self.repository_reader = repository_reader
        self.test_runner = test_runner
        self.committer = committer
        self.redis_client = redis_client

    def execute_incremental_changes(self, job_id: str, report_text: str, repo_name: str, branch_name: str, repository_type: str, completed_task_ids: Optional[List[str]] = None, pause_on_high_impact: bool = False, usuario_executor: Optional[str] = None) -> Dict[str, Any]:
        if not report_text or len(report_text.strip()) < 100:
            raise ValueError(f"[{job_id}] ERRO: report_text inválido para execução incremental. Tamanho: {len(report_text) if report_text else 0}")
        print(f"[{job_id}] [IncrementalOrchestrator] Iniciando com report_text de {len(report_text)} caracteres, repo={repo_name}, branch={branch_name}")
        tasks = self.report_parser.parse_implementation_plan(report_text)
        if not tasks:
            raise ValueError(f"[{job_id}] ERRO: Parser não retornou tarefas do relatório")
        print(f"[{job_id}] [IncrementalOrchestrator] Total de tarefas recebidas do parser: {len(tasks)}")
        for task in tasks:
            print(f"[{job_id}] [IncrementalOrchestrator] Tarefa {task.id}: step={task.step_number}, layer={task.layer}, action={task.action}, file={task.file_path}")
        codebase = self.repository_reader.read_repository(repo_name, branch_name, repository_type)
        for file_path, content in codebase.items():
            self.context_cache.cache_file_content(file_path, content)
        graph = self.dependency_analyzer.build_dependency_graph(tasks, codebase)
        levels = self.dependency_analyzer.topological_sort(graph)
        total_tasks_in_graph = sum(len(level) for level in levels)
        if total_tasks_in_graph != len(tasks):
            raise ValueError(f"Grafo de dependências incompleto. Tarefas extraídas: {len(tasks)}, Tarefas no grafo: {total_tasks_in_graph}")
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
        pr_urls = []
        pull_requests = []
        for level_index, level in enumerate(levels):
            print(f"[{job_id}] [IncrementalOrchestrator] Processando nível {level_index+1}/{len(levels)}, tarefas neste nível: {len(level)}")
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
            print(f"[{job_id}] [IncrementalOrchestrator] Aguardando conclusão de {len(sorted_level)} tarefas submetidas")
            with ThreadPoolExecutor(max_workers=3) as executor:
                for tid in sorted_level:
                    if tid in completed_tasks or tid in failed_tasks:
                        continue
                    print(f"[{job_id}] [IncrementalOrchestrator] Chamando apply_single_task para tarefa {tid} com job_id={job_id}")
                    task = all_tasks[tid]
                    context = self._build_task_context(task, completed_tasks)
                    future = executor.submit(self.agente_aplicador.apply_single_task, task, context, job_id, usuario_executor)
                    futures[future] = tid
                for future in as_completed(futures):
                    tid = futures[future]
                    try:
                        result = future.result()
                        print(f"[{job_id}] [IncrementalOrchestrator] Tarefa {tid} concluída. Sucesso: {result.success}")
                        self.context_cache.cache_task_context(tid, result)
                        if result.success:
                            completed_tasks[tid] = result
                            impacted_files = self.dependency_analyzer.analyze_task_impact(all_tasks[tid], codebase)
                            valid = self._validate_task_result(all_tasks[tid], result, impacted_files)
                            if valid:
                                commit_result = self.committer.create_incremental_commit(job_id, all_tasks[tid], result.modified_files, repo_name, branch_name, repository_type)
                                print(f"[{job_id}] [IncrementalOrchestrator] Commit criado para tarefa {tid}. PR URL: {commit_result.get('pr_url')}")
                                pr_url = commit_result.get('pr_url')
                                pr_urls.append(pr_url)
                                pull_requests.append({
                                    'branch_name': branch_name,
                                    'pr_url': pr_url,
                                    'task_ids': [tid]
                                })
                                print(f"[{job_id}] [IncrementalOrchestrator] Total de PRs criados até agora: {len(pull_requests)}")
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
            if self.redis_client:
                self.redis_client.set(checkpoint_key, json.dumps(checkpoint_data))
                print(f"[{job_id}] Checkpoint salvo: {len(completed_tasks)}/{len(all_tasks)} tarefas completadas")
        resumable = len(completed_tasks) < len(all_tasks)
        if not pull_requests or len(pull_requests) == 0:
            print(f"[{job_id}] WARNING: Nenhum PR foi criado durante a execução incremental. Tarefas completadas: {len(completed_tasks)}, Tarefas falhadas: {len(failed_tasks)}")
        for pr in pull_requests:
            print(f"[{job_id}] [IncrementalOrchestrator] PR criado: branch={pr.get('branch_name')}, url={pr.get('pr_url')}, tasks={pr.get('task_ids')}")
        result_summary = {
            "completed_tasks": list(completed_tasks.keys()),
            "failed_tasks": list(failed_tasks.keys()),
            "commits": [],
            "resumable": resumable,
            "high_impact_tasks": high_impact_tasks,
            "pr_urls": pr_urls,
            "pull_requests": pull_requests
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
        if self.redis_client:
            data = self.redis_client.get(checkpoint_key)
            if data:
                return json.loads(data)
        return None
