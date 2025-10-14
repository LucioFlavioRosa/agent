from typing import List, Dict
import logging

class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(changes: List[Dict]) -> List[Dict]:
        if not changes:
            return []
        changes_by_path = {}
        for change in changes:
            path = change.get('caminho')
            if not path:
                logging.error(f"[CONSOLIDATOR] Mudança sem caminho detectada: {change}")
                continue
            if path not in changes_by_path:
                changes_by_path[path] = []
            changes_by_path[path].append(change)
        consolidated = []
        for path, path_changes in changes_by_path.items():
            if len(path_changes) == 1:
                consolidated.append(path_changes[0])
                continue
            actions = [c.get('status') for c in path_changes]
            unique_actions = set(actions)
            if len(unique_actions) == 1:
                last_change = path_changes[-1]
                consolidated.append(last_change)
                continue
            logging.error(f"[CONSOLIDATOR][CONFLITO] Múltiplas ações conflitantes para o caminho '{path}': {actions} | Mudanças: {path_changes}")
            priority = {'REMOVIDO': 3, 'MODIFICADO': 2, 'CRIADO': 1, 'ADICIONADO': 1, 'CRIAR': 1}
            sorted_changes = sorted(path_changes, key=lambda c: priority.get(c.get('status'), 0), reverse=True)
            main_action = sorted_changes[0].get('status')
            main_change = sorted_changes[0].copy()
            if main_action in ('MODIFICADO', 'CRIADO', 'ADICIONADO', 'CRIAR'):
                for c in sorted_changes:
                    if c.get('conteudo') and c.get('conteudo') != main_change.get('conteudo'):
                        logging.warning(f"[CONSOLIDATOR][MERGE] Conteúdo diferente para o mesmo arquivo '{path}'. Prioridade para a última ação: {main_action}")
                        main_change['conteudo'] = c.get('conteudo')
            consolidated.append(main_change)
        return consolidated
