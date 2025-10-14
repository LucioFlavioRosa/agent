class PathNormalizer:
    @staticmethod
    def normalize(path: str) -> str:
        if not isinstance(path, str):
            return ''
        clean = path.strip().lstrip('/')
        if not clean:
            return ''
        return '/' + clean