from typing import List, Dict, Any

class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch: str) -> Dict[str, Any]:
        return {
            "branch": nome_branch,
            "commit_url": None,
            "pr_url": None,
            "success": False,
            "error": None,
            "message": None
        }

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch: Dict[str, Any], pr_url: str = None, message: str = None):
        resultado_branch["success"] = True
        if pr_url:
            resultado_branch["pr_url"] = pr_url
        if message:
            resultado_branch["message"] = message

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch: Dict[str, Any], error: str):
        resultado_branch["success"] = False
        resultado_branch["error"] = error

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas: List[Dict]):
        seen = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho")
            if caminho in seen:
                raise ValueError(f"Caminho duplicado detectado no conjunto_de_mudancas: {caminho}")
            seen.add(caminho)

    @staticmethod
    def _validate_commit_url(commit_url: str) -> bool:
        return isinstance(commit_url, str) and commit_url.startswith("https://") and "/commit/" in commit_url

    @staticmethod
    def _mesclar_conteudo(conteudo_existente: str, conteudo_novo: str) -> str:
        return conteudo_novo if conteudo_novo is not None else conteudo_existente

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas: List[Dict], resultado_branch: Dict[str, Any]) -> List[Dict]:
        mudancas_processadas = []
        from tools.repo_committers.path_normalizer import PathNormalizer
        for mudanca in conjunto_de_mudancas:
            nova_mudanca = mudanca.copy()
            if "caminho" in nova_mudanca:
                nova_mudanca["caminho"] = PathNormalizer.normalize(nova_mudanca["caminho"])
            mudancas_processadas.append(nova_mudanca)
        return mudancas_processadas
