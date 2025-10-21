from typing import List, Dict, Optional
from services.step_dependency_analyzer import StepDependencyAnalyzer
from services.change_consolidator_service import ChangeConsolidatorService
from services.report_table_parser import ReportTableParser

class IncrementalStepExecutorService:
    def __init__(self, report_table_parser=None):
        self.report_table_parser = report_table_parser or ReportTableParser()

    def get_step_batches_from_report(self, report_text: str, max_steps_per_batch: int = 3, transcricao_reuniao: Optional[str] = None) -> List[List[Dict]]:
        steps = self.report_table_parser.parse_report_table(report_text, transcricao_reuniao=transcricao_reuniao)
        if not steps:
            print(f"[INCREMENTAL] Nenhum step encontrado no relatório para batching.")
            return []
        print(f"[INCREMENTAL] {len(steps)} steps parseados do relatório.")
        batches = []
        current_batch = []
        for step in steps:
            if not current_batch:
                current_batch.append(step)
            else:
                dependent = any(
                    StepDependencyAnalyzer.are_steps_dependent(step, prev_step)
                    for prev_step in current_batch
                )
                if len(current_batch) < max_steps_per_batch and not dependent:
                    current_batch.append(step)
                else:
                    batches.append(current_batch)
                    current_batch = [step]
        if current_batch:
            batches.append(current_batch)
        print(f"[INCREMENTAL] {len(batches)} batches criados.")
        return batches

    def merge_all_batches(self, batch_results: List[Dict]) -> Dict[str, any]:
        resumo_geral = []
        conjunto_de_mudancas = []
        for batch in batch_results:
            if not isinstance(batch, dict):
                continue
            batch_resumo = batch.get("resumo_geral")
            if batch_resumo:
                resumo_geral.append(str(batch_resumo))
            batch_mudancas = batch.get("conjunto_de_mudancas")
            if isinstance(batch_mudancas, list):
                conjunto_de_mudancas.extend(batch_mudancas)
        conjunto_de_mudancas = ChangeConsolidatorService.consolidate_changes(conjunto_de_mudancas)
        return {
            "resumo_geral": " ".join(resumo_geral).strip(),
            "conjunto_de_mudancas": conjunto_de_mudancas
        }
