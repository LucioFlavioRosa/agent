import re

class PathNormalizer:
    @staticmethod
    def normalize(path: str) -> str:
        if path is None:
            return ''
        path = str(path).strip()
        if not path:
            return ''
        path = re.sub(r'/+', '/', path)  # substitui múltiplas barras por uma
        path = path.strip()
        if path.startswith('/'):
            # Remove todas as barras iniciais e adiciona uma barra
            path = '/' + path.lstrip('/')
        else:
            path = path.lstrip('/')  # caminho relativo não deve começar com barra
        return path