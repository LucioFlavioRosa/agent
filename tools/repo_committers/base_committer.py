class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch):
        return {
            "branch_name": nome_branch,
            "success": False,
            "commit_url": None,
            "pr_url": None,
            "message": None
        }

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch, pr_url=None, message=None):
        resultado_branch["success"] = True
        resultado_branch["pr_url"] = pr_url
        resultado_branch["message"] = message

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch, message):
        resultado_branch["success"] = False
        resultado_branch["message"] = message

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas):
        if not conjunto_de_mudancas:
            raise ValueError("Tentativa de commit com conjunto de mudanças vazio. Verifique a saída do agente e a formatação dos dados.")
        seen = set()
        for change in conjunto_de_mudancas:
            caminho = change.get('caminho')
            if caminho in seen:
                raise ValueError(f"Caminho duplicado detectado: {caminho}")
            seen.add(caminho)

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch):
        return conjunto_de_mudancas

    @staticmethod
    def _validate_commit_url(url):
        return isinstance(url, str) and url.startswith("http")

    @staticmethod
    def _mesclar_conteudo(conteudo_existente, conteudo_novo):
        return conteudo_novo
