from typing import List
import re

class PathNormalizer:
    @staticmethod
    def normalize(path: str) -> str:
        if not path or not isinstance(path, str):
            return ''
        path = path.replace('\\', '/').replace('//', '/')
        while '//' in path:
            path = path.replace('//', '/')
        path = re.sub(r'/+', '/', path)
        path = path.strip()
        if not path.startswith('/'):
            path = '/' + path
        return path

    @staticmethod
    def normalize_batch(paths: List[str]) -> List[str]:
        if not paths:
            return []
        return [PathNormalizer.normalize(p) for p in paths]

    @staticmethod
    def normalize_for_grouping(path: str) -> str:
        if not path or not isinstance(path, str):
            return ''
        path = path.replace('`', '')
        path = path.strip().lower()
        path = path.replace('\\', '/').replace('//', '/')
        while '//' in path:
            path = path.replace('//', '/')
        path = re.sub(r'/+', '/', path)
        path = path.replace(' ', '')
        return path
