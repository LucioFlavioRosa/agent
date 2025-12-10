from typing import List, Dict

class TaskDiscussionParserService:
    @staticmethod
    def parse_discussion_entries_from_markdown(markdown_table: str) -> List[Dict[str, str]]:
        if not markdown_table or not isinstance(markdown_table, str):
            return []
        lines = [line.strip() for line in markdown_table.splitlines() if line.strip()]
        if not lines:
            return []
        header = None
        entries = []
        for line in lines:
            if line.startswith('|') and line.endswith('|'):
                cols = [col.strip() for col in line.strip('|').split('|')]
                if not header:
                    header = cols
                    continue
                if len(cols) != len(header):
                    continue
                header_lower = [h.lower() for h in header]
                try:
                    idx_categoria = header_lower.index('categoria')
                    idx_pergunta = header_lower.index('pergunta')
                except ValueError:
                    return []
                categoria = cols[idx_categoria]
                pergunta = cols[idx_pergunta]
                entries.append({'categoria': categoria, 'pergunta': pergunta})
        return entries
