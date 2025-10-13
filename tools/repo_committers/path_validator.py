class PathValidator:
    @staticmethod
    def validate_path(caminho: str) -> str:
        if caminho is None:
            raise ValueError("PathValidator: caminho é None.")
        caminho_norm = str(caminho).strip()
        if not caminho_norm:
            raise ValueError(f"PathValidator: caminho vazio ou só espaços: '{caminho}'")
        return caminho_norm
