from typing import List, Dict, Any
import re

class TaskDiscussionParserService:
    @staticmethod
    def parse_discussion_entries_from_markdown(markdown: str) -> List[Dict[str, str]]:
        entries = []
        # Regex para encontrar linhas de categoria/pergunta em markdown
        pattern = re.compile(r'\|\s*Categoria\s*\|\s*Pergunta\s*\|\n(.*?)\n', re.DOTALL)
        match = pattern.search(markdown)
        if not match:
            return []
        table_content = match.group(1)
        for line in table_content.split('\n'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) >= 2:
                categoria = cols[0]
                pergunta = cols[1]
                if categoria or pergunta:
                    entries.append({'categoria': categoria, 'pergunta': pergunta})
        return entries
