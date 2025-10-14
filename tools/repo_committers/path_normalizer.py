class PathNormalizer:
    @staticmethod
    def normalize(path: str) -> str:
        if not isinstance(path, str):
            return ''
        path = path.strip()
        if not path:
            return ''
        path = path.lstrip('/')
        normalized = '/' + path if path else ''
        return normalized