import ast
import networkx as nx
from typing import List, Dict
from domain.models.incremental_change_models import CodeTask, TaskDependencyGraph

class DependencyAnalyzerService:
    def build_dependency_graph(self, tasks: List[CodeTask], codebase: Dict[str, str]) -> TaskDependencyGraph:
        graph = nx.DiGraph()
        task_map = {task.id: task for task in tasks}
        for task in tasks:
            graph.add_node(task.id)
        for task in tasks:
            for dep in task.dependencies:
                dep_task = next((t for t in tasks if t.file_path == dep), None)
                if dep_task:
                    graph.add_edge(dep_task.id, task.id)
        if not nx.is_directed_acyclic_graph(graph):
            raise Exception("Ciclo de dependência detectado entre tarefas.")
        adjacency_list = {node: list(graph.successors(node)) for node in graph.nodes}
        return TaskDependencyGraph(tasks=task_map, adjacency_list=adjacency_list)

    def topological_sort(self, graph: TaskDependencyGraph) -> List[List[str]]:
        G = nx.DiGraph()
        for node, successors in graph.adjacency_list.items():
            for succ in successors:
                G.add_edge(node, succ)
        levels = []
        sorted_nodes = list(nx.topological_sort(G))
        visited = set()
        while sorted_nodes:
            level = []
            for node in sorted_nodes:
                if all(pred in visited for pred in G.predecessors(node)):
                    level.append(node)
            if not level:
                break
            levels.append(level)
            for node in level:
                visited.add(node)
            sorted_nodes = [n for n in sorted_nodes if n not in visited]
        return levels

    def analyze_task_impact(self, task: CodeTask, codebase: Dict[str, str]) -> List[str]:
        impacted_files = []
        target_file = task.file_path
        for path, content in codebase.items():
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in target_file:
                                impacted_files.append(path)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in target_file:
                            impacted_files.append(path)
            except Exception:
                continue
        return impacted_files

    def detect_independent_task_groups(self, graph: TaskDependencyGraph) -> List[List[str]]:
        G = nx.DiGraph()
        for node, successors in graph.adjacency_list.items():
            for succ in successors:
                G.add_edge(node, succ)
        scc = list(nx.strongly_connected_components(G))
        groups = []
        for component in scc:
            group = list(component)
            if len(group) > 0:
                groups.append(group)
        print(f"Identificados {len(groups)} grupos independentes de tarefas para paralelização")
        return groups
