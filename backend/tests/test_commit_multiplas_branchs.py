import pytest
from unittest.mock import MagicMock
from tools import commit_multiplas_branchs

class DummyRepo:
    def __init__(self):
        self.created_files = []
        self.updated_files = []
        self.deleted_files = []
        self.prs = []
    def get_contents(self, path, ref):
        # Simula arquivo existente apenas se foi criado
        if path in self.created_files or path in self.updated_files:
            dummy = MagicMock()
            dummy.sha = f"sha-{path}"
            return dummy
        raise Exception("UnknownObjectException")
    def create_file(self, path, message, content, branch):
        self.created_files.append(path)
    def update_file(self, path, message, content, sha, branch):
        self.updated_files.append(path)
    def delete_file(self, path, message, sha, branch):
        self.deleted_files.append(path)
    def get_git_ref(self, ref):
        dummy = MagicMock()
        dummy.object.sha = "dummysha"
        return dummy
    def create_git_ref(self, ref, sha):
        pass
    def create_pull(self, title, body, head, base):
        pr = MagicMock()
        pr.html_url = f"https://github.com/testorg/testrepo/pull/{head}"
        self.prs.append(pr)
        return pr

def test_commit_direto_main_repo_novo(monkeypatch):
    # Monkeypatch o conector para sempre retornar DummyRepo
    monkeypatch.setattr(commit_multiplas_branchs, "GitHubConnector", MagicMock())
    commit_multiplas_branchs.GitHubConnector.connection = MagicMock(return_value=DummyRepo())
    # Simula grupo de mudanças
    dados_agrupados = {
        "grupos": [
            {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "main.py", "status": "ADICIONADO", "conteudo": "print('hello')"},
                    {"caminho_do_arquivo": "utils.py", "status": "ADICIONADO", "conteudo": "def x(): pass"}
                ]
            }
        ]
    }
    resultados = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
        nome_repo="testorg/testrepo",
        dados_agrupados=dados_agrupados,
        repo_novo=True
    )
    assert resultados[0]["branch_name"] == "main"
    assert resultados[0]["pr_url"] is None
    assert "main.py" in resultados[0]["arquivos_modificados"]
    assert "utils.py" in resultados[0]["arquivos_modificados"]
    assert "main" == resultados[0]["branch_name"]
    assert "Commits realizados diretamente na branch main" in resultados[0]["message"]

def test_commit_fluxo_antigo_pr(monkeypatch):
    dummy_repo = DummyRepo()
    monkeypatch.setattr(commit_multiplas_branchs, "GitHubConnector", MagicMock())
    commit_multiplas_branchs.GitHubConnector.connection = MagicMock(return_value=dummy_repo)
    dados_agrupados = {
        "grupos": [
            {
                "branch_sugerida": "feature-1",
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "main.py", "status": "ADICIONADO", "conteudo": "print('hello')"}
                ],
                "titulo_pr": "Add main.py",
                "resumo_do_pr": "Adiciona main.py"
            }
        ]
    }
    resultados = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
        nome_repo="testorg/testrepo",
        dados_agrupados=dados_agrupados,
        repo_novo=False
    )
    assert resultados[0]["branch_name"] == "feature-1"
    assert resultados[0]["pr_url"].startswith("https://github.com/testorg/testrepo/pull/")
    assert "main.py" in resultados[0]["arquivos_modificados"]
    assert "PR criado" in resultados[0]["message"]
