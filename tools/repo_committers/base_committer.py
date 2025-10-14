from typing import Dict, Any, List, Tuple

class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch: str) -> Dict[str, Any]:
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": None,
            "message": "",
            "arquivos_modificados": [],
            "commit_url": None
        }
    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas: list, resultado_branch: Dict[str, Any]) -> List[Dict[str, Any]]:
        mudancas_validas = []
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")
            if not caminho:
                continue
            mudancas_validas.append({
                "caminho": caminho,
                "status": status,
                "conteudo": conteudo,
                "justificativa": mudanca.get("justificativa", f"Aplicando mudança em {caminho}")
            })
            resultado_branch["arquivos_modificados"].append(caminho)
        return mudancas_validas
    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch: Dict[str, Any], pr_url: str = None, message: str = "PR criado.") -> None:
        if not pr_url or not isinstance(pr_url, str) or not pr_url.strip():
            raise ValueError(f"[ERRO][BaseCommitter] pr_url inválido recebido em _finalizar_resultado_sucesso: tipo={type(pr_url)}, valor={pr_url}, repr={repr(pr_url)}")
        resultado_branch["success"] = True
        resultado_branch["message"] = message
        resultado_branch["pr_url"] = pr_url.strip()
    @staticmethod
    def _finalizar_resultado_erro(resultado_branch: Dict[str, Any], error_message: str) -> None:
        resultado_branch["success"] = False
        resultado_branch["message"] = error_message
        if not resultado_branch.get("pr_url"):
            branch_name = resultado_branch.get("branch_name", "branch-desconhecida")
            resultado_branch["pr_url"] = f"ERRO: PR não criado para branch {branch_name}. {error_message}"
    @staticmethod
    def _mesclar_conteudo(conteudo_existente: str, novo_conteudo: str) -> str:
        if conteudo_existente is None:
            conteudo_existente = ""
        if novo_conteudo is None:
            novo_conteudo = ""
        return conteudo_existente + "\n\n" + novo_conteudo
    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas: List[Dict[str, Any]]) -> None:
        paths = [m.get('caminho_do_arquivo') or m.get('path') for m in conjunto_de_mudancas if m.get('caminho_do_arquivo') or m.get('path')]
        duplicates = set([p for p in paths if paths.count(p) > 1])
        if duplicates:
            raise ValueError(f"Há arquivos duplicados na lista de mudanças: {', '.join(duplicates)}")
    @staticmethod
    def _validate_file_exists_for_modification(mudanca: Dict, repo, branch_de_origem: str, repository_type: str) -> Tuple[bool, str]:
        status = mudanca.get("status", "").upper()
        caminho = mudanca.get("caminho_do_arquivo")
        if status != "MODIFICADO" or not caminho:
            return (True, "")
        from tools.repo_committers.branch_source_validator import BranchSourceValidator
        exists = BranchSourceValidator.validate_file_exists_in_branch(repo, caminho, branch_de_origem, repository_type)
        if not exists:
            return (False, f"Arquivo '{caminho}' não existe na branch de origem '{branch_de_origem}' para modificação. Considere usar status 'ADICIONADO' ou 'CRIADO'.")
        return (True, "")
    @staticmethod
    def _validate_files_exist_in_source(conjunto_de_mudancas: list, repo, branch_de_origem: str, repository_type: str):
        for mudanca in conjunto_de_mudancas:
            valid, msg = BaseCommitter._validate_file_exists_for_modification(mudanca, repo, branch_de_origem, repository_type)
            if not valid:
                return (False, msg)
        from tools.repo_committers.branch_source_validator import BranchSourceValidator
        for mudanca in conjunto_de_mudancas:
            status = mudanca.get("status", "").upper()
            caminho = mudanca.get("caminho_do_arquivo")
            if status == "MODIFICADO" and caminho:
                exists = BranchSourceValidator.validate_file_exists_in_branch(repo, caminho, branch_de_origem, repository_type)
                if not exists:
                    return (False, f"Arquivo '{caminho}' não existe na branch de origem '{branch_de_origem}' para o tipo de repositório '{repository_type}'.")
        return (True, "")
