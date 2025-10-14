from typing import List, Dict

class PathDeduplicator:
    @staticmethod
    def deduplicate_changes(changes: List[Dict]) -> List[Dict]:
        if not changes:
            return []
        dedup = {}
        for change in changes:
            caminho = change.get('caminho') or change.get('caminho_do_arquivo')
            status = change.get('status')
            if not caminho:
                continue
            if caminho in dedup:
                existing = dedup[caminho]
                if status == 'MODIFICADO' and existing.get('status') == 'MODIFICADO':
                    existing['conteudo'] = change.get('conteudo', existing.get('conteudo'))
                    existing['justificativa'] = change.get('justificativa', existing.get('justificativa'))
                else:
                    dedup[caminho] = change
            else:
                dedup[caminho] = change
        return list(dedup.values())
