from typing import Dict, Any
import yaml

class WorkflowRegistryLoader:
    def __init__(self, workflow_file_path: str):
        self.workflow_file_path = workflow_file_path

    def load_workflows(self) -> Dict[str, Any]:
        with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
            raw_yaml = yaml.safe_load(f)
        workflows = raw_yaml.get('workflows', {})
        # Filtra workflows que não dependem dos agentes removidos
        agentes_removidos = {'agente_processador', 'agente_revisor_codigo'}
        workflows_filtrados = {}
        for nome, workflow in workflows.items():
            steps = workflow.get('steps', [])
            agentes_utilizados = {step.get('agent') for step in steps if 'agent' in step}
            if not agentes_utilizados.intersection(agentes_removidos):
                workflows_filtrados[nome] = workflow
            else:
                # Ignora workflow que depende de agentes removidos
                continue
        return workflows_filtrados
