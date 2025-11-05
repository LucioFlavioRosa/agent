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

    # --- MÉTODO MODIFICADO ---
    @staticmethod
    def get_step_batches_from_report(report_text: str, max_steps_per_batch: int = 3) -> List[List[Dict]]:
        steps = IncrementalStepExecutorService.parse_report_table(report_text)
        if not steps:
            print(f"[INCREMENTAL] Nenhum step encontrado no relatório para batching.")
            return []
        print(f"[INCREMENTAL] {len(steps)} steps parseados do relatório.")

        # --- NOVA LÓGICA DE PRÉ-AGRUPAMENTO POR CAMINHO ---
        # Usamos um dict para agrupar steps pelo caminho normalizado.
        # Dicts em Python 3.7+ mantêm a ordem de inserção.
        path_groups: Dict[str, List[Dict]] = {}
        
        for step in steps:
            # Usar o _normalize_path do analyzer para consistência
            path = StepDependencyAnalyzer._normalize_path(step.get('Caminho do Arquivo', ''))
            
            # Se o caminho for vazio, tratar como um "step solto" único
            # para que ele caia na lógica de batching padrão.
            if not path:
                # Criar uma chave única para garantir que não seja agrupado
                unique_key = f"__no_path_step_{id(step)}__"
                path_groups[unique_key] = [step]
            else:
                if path not in path_groups:
                    path_groups[path] = []
                path_groups[path].append(step)
        
        # Esta é a nossa lista de grupos de steps (cada item é uma List[Dict])
        step_groups: List[List[Dict]] = list(path_groups.values())
        print(f"[INCREMENTAL] Steps pré-agrupados em {len(step_groups)} grupos por caminho.")
        # --- FIM DA NOVA LÓGICA DE PRÉ-AGRUPAMENTO ---

        batches = []
        current_batch_of_loose_steps = [] # Batch para "steps soltos" (grupos de 1)

        for step_group in step_groups:
            
            if len(step_group) > 1:
                # REGRA 1: "primeiro devemos colocar todas as linhas com mesmo nome no mesmo batch"
                # Este grupo tem múltiplas linhas com o mesmo caminho.
                
                # 1. Salva (flush) o batch atual de steps soltos, se existir
                if current_batch_of_loose_steps:
                    batches.append(current_batch_of_loose_steps)
                    print(f"[INCREMENTAL] Criado batch de {len(current_batch_of_loose_steps)} steps soltos.")
                    current_batch_of_loose_steps = []
                
                # 2. Adiciona este grupo como seu próprio batch, independente do tamanho
                batches.append(step_group)
                print(f"[INCREMENTAL] Criado batch dedicado para {len(step_group)} steps (mesmo caminho).")

            else:
                # REGRA 2: "somente se nao houver linhas com mesmo caminho deve valer a regra..."
                # Este é um "step solto" (grupo de 1). Aplicar a lógica de batching padrão.
                step = step_group[0]
                
                if not current_batch_of_loose_steps:
                    # Inicia um novo batch de steps soltos
                    current_batch_of_loose_steps.append(step)
                else:
                    # Verifica dependência contra o batch de steps soltos atual
                    dependent = any(
                        StepDependencyAnalyzer.are_steps_dependent(step, prev_step)
                        for prev_step in current_batch_of_loose_steps
                    )
                    
                    if len(current_batch_of_loose_steps) < max_steps_per_batch and not dependent:
                        # Adiciona ao batch de steps soltos
                        current_batch_of_loose_steps.append(step)
                    else:
                        # Fecha o batch de steps soltos e inicia um novo
                        batches.append(current_batch_of_loose_steps)
                        print(f"[INCREMENTAL] Criado batch de {len(current_batch_of_loose_steps)} steps soltos.")
                        current_batch_of_loose_steps = [step]

        # Não esquecer o último batch de steps soltos
        if current_batch_of_loose_steps:
            batches.append(current_batch_of_loose_steps)
            print(f"[INCREMENTAL] Criado batch final de {len(current_batch_of_loose_steps)} steps soltos.")

        print(f"[INCREMENTAL] {len(batches)} batches criados no total.")
        return batches
    # --- FIM DO MÉTODO MODIFICADO ---

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
