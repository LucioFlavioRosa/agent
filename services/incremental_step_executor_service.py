from typing import List, Dict, Optional
from services.step_dependency_analyzer import StepDependencyAnalyzer
from services.change_consolidator_service import ChangeConsolidatorService
import re

class IncrementalStepExecutorService:
    @staticmethod
    def parse_report_table(report_text: str) -> List[Dict]:
        if not report_text or '|' not in report_text:
            return []
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        table_lines = []
        header_found = False
        for line in lines:
            if re.match(r'^\|.*\|$', line):
                if re.match(r'^\|[\s\-\|]+\|$', line):
                    continue
                if not header_found:
                    header_found = True
                table_lines.append(line)
            elif header_found:
                break
        if len(table_lines) < 2:
            return []
        headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
        rows = table_lines[1:]
        result = []
        for row in rows:
            if re.match(r'^\|[\s\-\|]+\|$', row):
                continue
            cols = [c.strip() for c in row.strip('|').split('|')]
            if len(cols) != len(headers):
                continue
            row_dict = dict(zip(headers, cols))
            result.append(row_dict)
        return result

    @staticmethod
    def get_step_batches_from_report(report_text: str, max_steps_per_batch: int = 3) -> List[List[Dict]]:
        steps = IncrementalStepExecutorService.parse_report_table(report_text)
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

    @staticmethod
    def merge_all_batches(batch_results: List[Dict]) -> Dict[str, any]:
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
