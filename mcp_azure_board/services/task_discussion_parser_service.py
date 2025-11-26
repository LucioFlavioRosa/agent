from typing import List, Dict
import re

class TaskDiscussionParserService:
    @staticmethod
    def parse_discussion_entries_from_markdown(markdown: str) -> List[Dict[str, str]]:
        entries = []
        lines = markdown.strip().splitlines()
        header_found = False
        header = []
        for line in lines:
            if not header_found and line.strip().startswith('|') and 'Categoria' in line and 'Pergunta' in line:
                header = [h.strip().lower() for h in line.strip('|').split('|')]
                header_found = True
                continue
            if header_found and line.strip().startswith('|'):
                cols = [col.strip() for col in line.strip('|').split('|')]
                if len(cols) == len(header):
                    entry = dict(zip(header, cols))
                    entries.append(entry)
        return entries
