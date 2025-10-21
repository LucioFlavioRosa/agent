import re
from typing import List, Dict, Optional

class ReportTableParser:
    def parse_report_table(self, report_text: str, transcricao_reuniao: Optional[str] = None) -> List[Dict]:
        if not report_text or '|' not in report_text:
            return []
        if '| ID | Épico | Objetivo de Negócio |' in report_text:
            return self.parse_epicos_table(report_text)
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

    def parse_epicos_table(self, report_text: str) -> List[Dict]:
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        table_start = None
        for idx, line in enumerate(lines):
            if line.startswith('| ID |'):
                table_start = idx
                break
        if table_start is None:
            return []
        header = lines[table_start]
        separator = lines[table_start + 1] if table_start + 1 < len(lines) else ''
        data_lines = lines[table_start + 2:]
        headers = [h.strip() for h in header.strip('|').split('|')]
        epicos = []
        for line in data_lines:
            if not line.startswith('|') or line == separator:
                continue
            cols = [col.strip() for col in line.strip('|').split('|')]
            if len(cols) != len(headers):
                continue
            epico_dict = dict(zip(headers, cols))
            epicos.append(epico_dict)
        return epicos
