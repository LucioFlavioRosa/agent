from typing import List, Dict

class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch):
        return {
            "branch": nome_branch,
            "commit_url": None,
            "pr_url": None,
            "success": False,
            "error": None,
            "message": None
        }

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch, msg):
        resultado_branch["success"] = False
        resultado_branch["error"] = msg
        return resultado_branch

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch, pr_url=None, message=None):
        resultado_branch["success"] = True
        if pr_url:
            resultado_branch["pr_url"] = pr_url
        if message:
            resultado_branch["message"] = message
        return resultado_branch

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas: List[Dict]):
        seen = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho")
            if caminho in seen:
                raise ValueError(f"Caminho duplicado detectado no conjunto_de_mudancas: {caminho}")
            seen.add(caminho)

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch):
        # Dummy implementation for context
        return conjunto_de_mudancas

    @staticmethod
    def _validate_commit_url(url):
        # Dummy implementation for context
        return isinstance(url, str) and url.startswith("http")

    @staticmethod
    def _mesclar_conteudo(conteudo_existente, conteudo_novo):
        # Dummy implementation for context
        return conteudo_novo
