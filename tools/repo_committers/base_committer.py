from typing import List, Dict, Any

class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch: str) -> Dict[str, Any]:
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": None,
            "message": None,
            "arquivos_modificados": [],
            "commit_url": None
        }

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch: Dict[str, Any], pr_url: str = None, message: str = None):
        resultado_branch["success"] = True
        if pr_url:
            resultado_branch["pr_url"] = pr_url
        if message:
            resultado_branch["message"] = message
        return resultado_branch

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch: Dict[str, Any], message: str):
        resultado_branch["success"] = False
        resultado_branch["message"] = message
        return resultado_branch

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas: List[Dict[str, Any]]):
        paths = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho")
            if caminho in paths:
                raise ValueError(f"Arquivo duplicado na lista de mudanças: {caminho}")
            paths.add(caminho)

    @staticmethod
    def _validate_commit_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        return url.startswith('http://') or url.startswith('https://') or "Branch processada" in url or "PR criado" in url or "MR criado" in url

    @staticmethod
    def _mesclar_conteudo(conteudo_existente: str, conteudo_novo: str) -> str:
        if conteudo_existente is None:
            return conteudo_novo or ""
        if conteudo_novo is None:
            return conteudo_existente or ""
        return conteudo_existente + "\n" + conteudo_novo

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas: List[Dict[str, Any]], resultado_branch: Dict[str, Any]) -> List[Dict[str, Any]]:
        mudancas_validas = []
        for mudanca in conjunto_de_mudancas:
            status = mudanca.get("status")
            caminho = mudanca.get("caminho")
            conteudo = mudanca.get("conteudo")
            if status in ("ADICIONADO", "CRIADO", "MODIFICADO"):
                if conteudo is None or (isinstance(conteudo, str) and conteudo.strip() == ""):
                    print(f"[ERRO][BaseCommitter] Mudança ignorada: arquivo '{caminho}' com status '{status}' possui conteudo vazio ou None.")
                    continue
            mudancas_validas.append(mudanca)
        return mudancas_validas
