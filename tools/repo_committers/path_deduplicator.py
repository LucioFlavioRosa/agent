class PathDeduplicator:
    @staticmethod
    def deduplicate_changes(changes):
        if not changes:
            return []
        seen = set()
        deduped = []
        for change in changes:
            caminho = change.get('caminho')
            if caminho and caminho not in seen:
                seen.add(caminho)
                deduped.append(change)
        return deduped
