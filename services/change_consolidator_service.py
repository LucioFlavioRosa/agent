import logging
from collections import defaultdict

class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(conjunto_de_mudancas):
        if not conjunto_de_mudancas:
            return []
        changes_by_path = defaultdict(list)
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get('caminho')
            if not caminho:
                continue
            changes_by_path[caminho].append(mudanca)
        resultado = []
        for caminho, mudancas in changes_by_path.items():
            if len(mudancas) == 1:
                resultado.append(mudancas[0])
                continue
            # Detectar conflitos de ações
            acoes = set(m.get('status') for m in mudancas)
            if len(acoes) > 1:
                logging.error(f"[MERGE_BATCHES][CONSOLIDATE] Conflito detectado para o caminho '{caminho}': ações conflitantes {acoes}. Mudanças: {mudancas}")
                # Estratégia: priorizar CRIAR > MODIFICADO > ADICIONADO > REMOVIDO, ou a última ação
                prioridade = ['CRIAR', 'CRIADO', 'ADICIONADO', 'MODIFICADO', 'REMOVIDO']
                mudanca_final = None
                for acao in prioridade:
                    for m in reversed(mudancas):
                        if m.get('status') == acao:
                            mudanca_final = m.copy()
                            break
                    if mudanca_final:
                        break
                if not mudanca_final:
                    mudanca_final = mudancas[-1].copy()
                logging.error(f"[MERGE_BATCHES][CONSOLIDATE] Mudança mesclada para '{caminho}': {mudanca_final}")
                resultado.append(mudanca_final)
            else:
                # Mesclar conteúdo se possível, priorizando a última mudança
                mudanca_final = mudancas[-1].copy()
                resultado.append(mudanca_final)
        return resultado
