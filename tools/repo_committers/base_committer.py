class BaseCommitter:
    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas):
        seen = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho")
            if caminho in seen:
                raise ValueError(f"Caminho duplicado detectado no conjunto_de_mudancas: {caminho}")
            seen.add(caminho)
