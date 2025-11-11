from typing import List, Dict, Any

class FeatureParserService:
    @staticmethod
    def parse_features_from_markdown(markdown_table: str) -> List[Dict[str, Any]]:
        if not markdown_table or not isinstance(markdown_table, str):
            return []
        lines = [line for line in markdown_table.splitlines() if line.strip() and not line.strip().startswith('|---')]
        if not lines:
            return []
        header = None
        features = []
        for line in lines:
            if line.startswith('|') and line.endswith('|'):
                cols = [col.strip() for col in line.strip('|').split('|')]
                if not header:
                    header = cols
                    continue
                if len(cols) != len(header):
                    continue
                feature = dict(zip(header, cols))
                features.append(feature)
        return features
