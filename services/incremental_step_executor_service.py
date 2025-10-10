import re
from typing import List, Dict, Any
from services.step_dependency_analyzer import StepDependencyAnalyzer

class IncrementalStepExecutorService:
    @staticmethod
    def parse_markdown_table(report_text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        table_start = None
        for idx, line in enumerate(lines):
            if line.startswith('|') and 'Passo #' in line:
                table_start = idx
                break
        if table_start is None or table_start + 2 >= len(lines):
            return []
        header = [h.strip() for h in lines[table_start].strip('|').split('|')]
        data_lines = []
        for line in lines[table_start+2:]:
            if not line.startswith('|'):
                break
            data_lines.append(line)
        steps = []
        for line in data_lines:
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) != len(header):
                continue
            step = dict(zip(header, cols))
            steps.append(step)
        return steps

    @staticmethod
    def normalize_step(step: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'numero': step.get('Passo #') or step.get('Passo'),
            'camada': step.get('Camada'),
            'acao': step.get('Ação') or step.get('Acao'),
            'caminho': step.get('Caminho do Arquivo') or step.get('Arquivo'),
            'descricao': step.get('Descrição') or step.get('Descricao'),
            'tempo_estimado': step.get('Tempo Estimado') or step.get('Tempo'),
            'raw': step
        }

    @classmethod
    def extract_steps(cls, report_text: str) -> List[Dict[str, Any]]:
        steps = cls.parse_markdown_table(report_text)
        return [cls.normalize_step(s) for s in steps]

    @classmethod
    def group_steps_into_batches(cls, steps: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        batches = []
        pending = steps.copy()
        while pending:
            batch = []
            used = set()
            for i, step in enumerate(pending):
                dependent = False
                for bstep in batch:
                    if StepDependencyAnalyzer.are_steps_dependent(bstep, step):
                        dependent = True
                        break
                if not dependent:
                    batch.append(step)
                    used.add(i)
            pending = [step for idx, step in enumerate(pending) if idx not in used]
            batches.append(batch)
        return batches

    @classmethod
    def get_step_batches_from_report(cls, report_text: str) -> List[List[Dict[str, Any]]]:
        steps = cls.extract_steps(report_text)
        return cls.group_steps_into_batches(steps)
