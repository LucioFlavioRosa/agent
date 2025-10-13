class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(conjunto_de_mudancas):
        if not conjunto_de_mudancas or not isinstance(conjunto_de_mudancas, list):
            return []
        mudancas_normalizadas = []
        for idx, mudanca in enumerate(conjunto_de_mudancas):
            if 'caminho' not in mudanca:
                if 'caminho_do_arquivo' in mudanca:
                    mudanca['caminho'] = mudanca['caminho_do_arquivo']
                    print(f"[CONSOLIDATE][NORMALIZAÇÃO] Mudança {idx}: 'caminho' ausente, copiado de 'caminho_do_arquivo'.")
                else:
                    print(f"[CONSOLIDATE][ERRO] Mudança {idx}: ambas as chaves 'caminho' e 'caminho_do_arquivo' ausentes. Mudança removida: {mudanca}")
                    continue
            mudancas_normalizadas.append(mudanca)
        # Aqui pode-se adicionar lógica extra de consolidação se necessário
        return mudancas_normalizadas
