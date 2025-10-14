from typing import List, Dict

class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(changes: List[Dict]) -> List[Dict]:
        if not changes:
            return []
        consolidated = {}
        for change in changes:
            caminho = change.get('caminho') or change.get('caminho_do_arquivo')
            if not caminho:
                continue
            status = change.get('status')
            if caminho in consolidated:
                existing = consolidated[caminho]
                if status == 'MODIFICADO' and existing.get('status') == 'MODIFICADO':
                    # Mesclar conteúdos (mantém o último conteúdo)
                    existing['conteudo'] = change.get('conteudo', existing.get('conteudo'))
                    existing['justificativa'] = change.get('justificativa', existing.get('justificativa'))
                else:
                    # Para outros status, mantém a última ocorrência
                    consolidated[caminho] = change
            else:
                consolidated[caminho] = change
        return list(consolidated.values())
