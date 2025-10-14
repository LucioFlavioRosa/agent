class PathDeduplicator:
    @staticmethod
    def validate_changes_before_deduplication(conjunto_de_mudancas):
        mudancas_validas = []
        mudancas_invalidas = []
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get('caminho')
            if caminho is None or caminho == '':
                print(f"[ERROR][DEDUPLICATOR] Mudança inválida detectada e removida: {mudanca}")
                mudancas_invalidas.append(mudanca)
            else:
                mudancas_validas.append(mudanca)
        return mudancas_validas, mudancas_invalidas

    @staticmethod
    def deduplicate_changes(conjunto_de_mudancas):
        mudancas_validas, mudancas_invalidas = PathDeduplicator.validate_changes_before_deduplication(conjunto_de_mudancas)
        caminhos_vistos = set()
        resultado = []
        for mudanca in mudancas_validas:
            caminho = mudanca.get('caminho')
            if caminho in caminhos_vistos:
                print(f"[WARN][DEDUPLICATOR] Caminho duplicado detectado e ignorado: {caminho}")
                continue
            caminhos_vistos.add(caminho)
            resultado.append(mudanca)
        return resultado
