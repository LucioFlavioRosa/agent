from typing import List, Dict, Any

class ChangeConsolidatorService:
    @staticmethod
    def consolidate_changes(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        consolidated = {}
        remove_paths = set()
        for change in changes:
            # Passo 2: normalização de chaves de caminho
            if 'caminho' not in change:
                if 'caminho_do_arquivo' in change:
                    change['caminho'] = change['caminho_do_arquivo']
                elif 'path' in change:
                    change['caminho'] = change['path']
            path = change.get('caminho')
            status = (change.get('status') or change.get('action') or '').upper()
            conteudo = change.get('conteudo') or change.get('content')
            if not path:
                print(f"[CONSOLIDATE][SKIP] Mudança sem caminho: {change}")
                continue
            if path in remove_paths:
                print(f"[CONSOLIDATE][SKIP] Caminho '{path}' já marcado para remoção, ignorando mudança: {change}")
                continue
            if path in consolidated:
                prev = consolidated[path]
                prev_status = (prev.get('status') or prev.get('action') or '').upper()
                # ADICIONADO/CRIADO + MODIFICADO => manter ADICIONADO com conteúdo final
                if prev_status in ('ADICIONADO', 'CRIADO') and status == 'MODIFICADO':
                    print(f"[CONSOLIDATE] Mantendo ADICIONADO/CRIADO, descartando MODIFICADO para arquivo '{path}'")
                    prev['conteudo'] = conteudo
                    prev['status'] = prev_status
                    continue
                # MODIFICADO + REMOVIDO => manter apenas REMOVIDO
                if prev_status == 'MODIFICADO' and status == 'REMOVIDO':
                    print(f"[CONSOLIDATE] MODIFICADO + REMOVIDO: Mantendo apenas REMOVIDO para arquivo '{path}'")
                    consolidated[path] = {
                        **change,
                        'status': 'REMOVIDO',
                        'conteudo': None
                    }
                    continue
                # ADICIONADO/CRIADO + REMOVIDO => remover ambas
                if prev_status in ('ADICIONADO', 'CRIADO') and status == 'REMOVIDO':
                    print(f"[CONSOLIDATE] ADICIONADO/CRIADO + REMOVIDO: Removendo ambas para arquivo '{path}'")
                    del consolidated[path]
                    remove_paths.add(path)
                    continue
                # Para outros casos, a última operação prevalece
                print(f"[CONSOLIDATE] Última operação prevalece para arquivo '{path}': status anterior '{prev_status}', novo status '{status}'")
                consolidated[path] = {**change, 'status': status, 'conteudo': conteudo}
            else:
                print(f"[CONSOLIDATE] Nova entrada para arquivo '{path}': status '{status}'")
                consolidated[path] = {**change, 'status': status, 'conteudo': conteudo}
        resultado = [v for k, v in consolidated.items() if k not in remove_paths]
        print(f"[CONSOLIDATE][RESULT] Total de arquivos consolidados: {len(resultado)}")
        return resultado
