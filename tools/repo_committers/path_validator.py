from typing import Dict, Optional
import os

class PathValidator:
    @staticmethod
    def normalize_change_keys(change: Dict) -> Dict:
        # Cria uma cópia para não alterar o original
        change = dict(change) if change is not None else {}
        # Normaliza as chaves de caminho
        if 'caminho' not in change:
            if 'caminho_do_arquivo' in change and change['caminho_do_arquivo']:
                change['caminho'] = change['caminho_do_arquivo']
            elif 'path' in change and change['path']:
                change['caminho'] = change['path']
        return change

    @staticmethod
    def validate_path(caminho_or_change: Optional[object]) -> str:
        # Se for dict, normaliza e extrai caminho
        if isinstance(caminho_or_change, dict):
            change = PathValidator.normalize_change_keys(caminho_or_change)
            caminho = change.get('caminho')
        else:
            caminho = caminho_or_change
        if caminho is None:
            raise Exception('PathValidator: caminho é None.')
        caminho = caminho.strip()
        if not caminho:
            raise Exception('PathValidator: caminho está vazio.')
        # Caminho não pode ter caracteres proibidos
        if any(x in caminho for x in ['..', '~', '//', '\\']):
            raise Exception(f'PathValidator: caminho inválido (sequência proibida): {caminho}')
        # Caminho não pode ser absoluto
        if os.path.isabs(caminho):
            raise Exception(f'PathValidator: caminho absoluto não permitido: {caminho}')
        # Caminho não pode começar com /
        if caminho.startswith('/') or caminho.startswith('\\'):
            raise Exception(f'PathValidator: caminho não pode começar com barra: {caminho}')
        return caminho
