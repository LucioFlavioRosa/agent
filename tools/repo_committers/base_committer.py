class BaseCommitter:
    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas):
        caminhos_vistos = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho")
            if not caminho:
                continue
            if caminho in caminhos_vistos:
                raise ValueError(f"Caminho duplicado detectado no conjunto_de_mudancas: {caminho}")
            caminhos_vistos.add(caminho)
