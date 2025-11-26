import re
from typing import List, Dict

class TaskParserService:
    def parse_tasks_from_markdown(self, markdown_table: str) -> List[Dict[str, str]]:
        lines = [line for line in markdown_table.strip().splitlines() if line.strip() and not line.strip().startswith('|---')]
        if len(lines) < 2:
            return []
        header_line = lines[0].strip()
        if header_line.startswith('|'):
            header_line = header_line[1:]
        if header_line.endswith('|'):
            header_line = header_line[:-1]
        header = [h.strip().lower().replace(' ', '_') for h in header_line.split('|')]
        tasks = []
        for line in lines[1:]:
            line = line.strip()
            if not line.startswith('|'):
                continue
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
            cols = [col.strip() for col in line.split('|')]
            if len(cols) == len(header):
                try:
                    task = dict(zip(header, cols))
                    tasks.append(task)
                except Exception:
                    continue
        return tasks
