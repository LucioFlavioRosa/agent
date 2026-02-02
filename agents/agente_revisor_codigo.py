import os
from typing import List

class AgenteRevisorCodigo:
    """
    Agente responsável por revisar e sugerir melhorias no código de um repositório.
    Este agente é genérico e não depende de integrações externas como Azure Boards.
    """
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def listar_arquivos_codigo(self, extensoes: List[str] = None) -> List[str]:
        """
        Lista todos os arquivos de código no repositório com as extensões especificadas.
        """
        if extensoes is None:
            extensoes = ['.py', '.js', '.java', '.cs']
        arquivos_codigo = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensoes):
                    arquivos_codigo.append(os.path.join(root, file))
        return arquivos_codigo

    def revisar_arquivo(self, caminho_arquivo: str) -> dict:
        """
        Realiza uma revisão simples do arquivo de código, retornando sugestões de melhoria.
        """
        sugestoes = []
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            if len(linhas) > 500:
                sugestoes.append('Arquivo muito extenso, considere dividir em módulos menores.')
            if any('TODO' in linha for linha in linhas):
                sugestoes.append('Existem comentários TODO no código, revise-os.')
            # Outras regras simples podem ser adicionadas aqui
        except Exception as e:
            return {'arquivo': caminho_arquivo, 'erro': str(e)}
        return {'arquivo': caminho_arquivo, 'sugestoes': sugestoes}

    def revisar_repositorio(self) -> List[dict]:
        """
        Executa revisão em todos os arquivos do repositório.
        """
        resultados = []
        arquivos = self.listar_arquivos_codigo()
        for arquivo in arquivos:
            resultado = self.revisar_arquivo(arquivo)
            resultados.append(resultado)
        return resultados
