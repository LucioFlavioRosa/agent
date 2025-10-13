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
                continue
            if path in remove_paths:
                continue
            if path in consolidated:
                prev = consolidated[path]
                prev_status = (prev.get('status') or prev.get('action') or '').upper()
                # ADICIONADO/CRIADO + MODIFICADO => manter ADICIONADO com conteúdo final
                if prev_status in ('ADICIONADO', 'CRIADO') and status == 'MODIFICADO':
                    prev['conteudo'] = conteudo
                    prev['status'] = prev_status
                    continue
                # MODIFICADO + REMOVIDO => manter apenas REMOVIDO
                if prev_status == 'MODIFICADO' and status == 'REMOVIDO':
                    consolidated[path] = {
                        **change,
                        'status': 'REMOVIDO',
                        'conteudo': None
                    }
                    continue
                # ADICIONADO/CRIADO + REMOVIDO => remover ambas
                if prev_status in ('ADICIONADO', 'CRIADO') and status == 'REMOVIDO':
                    del consolidated[path]
                    remove_paths.add(path)
                    continue
                # Para outros casos, a última operação prevalece
                consolidated[path] = {**change, 'status': status, 'conteudo': conteudo}
            else:
                consolidated[path] = {**change, 'status': status, 'conteudo': conteudo}
        return [v for k, v in consolidated.items() if k not in remove_paths]
