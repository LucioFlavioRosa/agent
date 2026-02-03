from typing import Dict, Any
import yaml

class WorkflowRegistryLoader:
    def __init__(self, workflow_file_path: str):
        self.workflow_file_path = workflow_file_path

    def load_workflows(self) -> Dict[str, Any]:
        with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
            raw_yaml = yaml.safe_load(f)
        workflows = raw_yaml.get('workflows', {})
        agentes_removidos = {'agente_processador', 'agente_revisor_codigo'}
        workflows_filtrados = {}
        for nome, workflow in workflows.items():
            steps = workflow.get('steps', [])
            agentes_utilizados = set()
            for step in steps:
                agent = step.get('agent')
                if agent:
                    agentes_utilizados.add(agent)
            if not any(agent in agentes_removidos for agent in agentes_utilizados):
                workflows_filtrados[nome] = workflow
        return workflows_filtrados
