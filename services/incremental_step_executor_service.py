from typing import List, Dict, Optional
from services.step_dependency_analyzer import StepDependencyAnalyzer
from services.change_consolidator_service import ChangeConsolidatorService
import re
import json

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
        current_batch_paths = set()
        file_to_batch_index = {}
        for idx, step in enumerate(steps):
            step_path = StepDependencyAnalyzer._normalize_path(step.get('Caminho do Arquivo', ''))
            print(f"[INCREMENTAL][DEBUG] Iteração {idx}: step_path='{step_path}'")
            if step_path in file_to_batch_index:
                batch_idx = file_to_batch_index[step_path]
                if batch_idx < len(batches):
                    batches[batch_idx].append(step)
                    print(f"[INCREMENTAL][BATCHING] Step {idx+1} adicionado ao batch existente {batch_idx} para arquivo '{step_path}'")
                    print(f"[INCREMENTAL][DEBUG] file_to_batch_index: {file_to_batch_index}")
                    print(f"[INCREMENTAL][DEBUG] batches[{batch_idx}] tamanho: {len(batches[batch_idx])}")
                else:
                    print(f"[INCREMENTAL][ERRO] batch_idx {batch_idx} fora do range de batches (len={len(batches)}), step {idx+1}")
                continue
            if not current_batch:
                current_batch.append(step)
                if step_path:
                    current_batch_paths.add(step_path)
                print(f"[INCREMENTAL][DEBUG] Novo current_batch iniciado com step {idx+1}, arquivos: {list(current_batch_paths)}")
                continue
            if len(current_batch) < max_steps_per_batch:
                current_batch.append(step)
                if step_path:
                    current_batch_paths.add(step_path)
                print(f"[INCREMENTAL][DEBUG] Step {idx+1} adicionado ao current_batch, tamanho atual: {len(current_batch)}")
                continue
            batches.append(current_batch)
            for p in current_batch_paths:
                file_to_batch_index[p] = len(batches) - 1
            print(f"[INCREMENTAL][BATCHING] Batch {len(batches)-1} criado com {len(current_batch)} steps: arquivos {list(current_batch_paths)}")
            print(f"[INCREMENTAL][DEBUG] file_to_batch_index após fechamento de batch: {file_to_batch_index}")
            current_batch = [step]
            current_batch_paths = set()
            if step_path:
                current_batch_paths.add(step_path)
            print(f"[INCREMENTAL][DEBUG] Novo current_batch iniciado com step {idx+1}, arquivos: {list(current_batch_paths)}")
        if current_batch:
            batches.append(current_batch)
            for p in current_batch_paths:
                file_to_batch_index[p] = len(batches) - 1
            print(f"[INCREMENTAL][BATCHING] Batch {len(batches)-1} criado com {len(current_batch)} steps: arquivos {list(current_batch_paths)}")
            print(f"[INCREMENTAL][DEBUG] file_to_batch_index após fechamento final: {file_to_batch_index}")
        print(f"[INCREMENTAL] {len(batches)} batches criados.")
        return batches

    @staticmethod
    def merge_all_batches(batch_results: List[Dict]) -> Dict[str, any]:
        print(f"[INCREMENTAL][MERGE] batch_results recebido para merge_all_batches: {json.dumps(batch_results, default=str) if batch_results else '[]'}")
        resumo_geral = []
        conjunto_de_mudancas = []
        if not batch_results or not isinstance(batch_results, list):
            print(f"[INCREMENTAL][MERGE][AVISO] batch_results está vazio ou malformado. Retornando estrutura padrão vazia.")
            return {
                "resumo_geral": "",
                "conjunto_de_mudancas": []
            }
        for batch in batch_results:
            if not isinstance(batch, dict):
                continue
            batch_resumo = batch.get("resumo_geral")
            if batch_resumo:
                resumo_geral.append(str(batch_resumo))
            batch_mudancas = batch.get("conjunto_de_mudancas")
            if isinstance(batch_mudancas, list):
                conjunto_de_mudancas.extend(batch_mudancas)
        print(f"[INCREMENTAL][MERGE] conjunto_de_mudancas antes da consolidação: {json.dumps(conjunto_de_mudancas, default=str)}")
        conjunto_de_mudancas = ChangeConsolidatorService.consolidate_changes(conjunto_de_mudancas)
        print(f"[INCREMENTAL][MERGE] conjunto_de_mudancas após consolidação: {json.dumps(conjunto_de_mudancas, default=str)}")
        return {
            "resumo_geral": " ".join(resumo_geral).strip(),
            "conjunto_de_mudancas": conjunto_de_mudancas
        }
