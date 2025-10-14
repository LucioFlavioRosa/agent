class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(changes):
        if not changes:
            return []
        consolidated = {}
        for change in changes:
            caminho = change.get('caminho')
            if not caminho:
                continue
            consolidated[caminho] = change
        return list(consolidated.values())
