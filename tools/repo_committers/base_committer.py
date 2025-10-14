class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch):
        return {
            'branch_name': nome_branch,
            'commit_url': None,
            'pr_url': None,
            'message': None,
            'success': False,
            'error': None
        }

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch, pr_url=None, message=None):
        resultado_branch['success'] = True
        if pr_url:
            resultado_branch['pr_url'] = pr_url
        if message:
            resultado_branch['message'] = message
        if 'branch_name' not in resultado_branch:
            raise ValueError("Resultado de branch deve conter a chave 'branch_name'")
        return resultado_branch

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch, error_message):
        resultado_branch['success'] = False
        resultado_branch['error'] = error_message
        if 'branch_name' not in resultado_branch:
            raise ValueError("Resultado de branch deve conter a chave 'branch_name'")
        return resultado_branch

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas):
        paths = set()
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get('caminho')
            if caminho in paths:
                raise ValueError(f"Mudança duplicada detectada para o caminho: {caminho}")
            paths.add(caminho)

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch):
        # Mantém apenas mudanças válidas (com caminho e status)
        mudancas_validas = []
        for mudanca in conjunto_de_mudancas:
            if mudanca.get('caminho') and mudanca.get('status'):
                mudancas_validas.append(mudanca)
        return mudancas_validas

    @staticmethod
    def _validate_commit_url(url):
        return url and isinstance(url, str) and url.startswith('http')

    @staticmethod
    def _mesclar_conteudo(conteudo_existente, conteudo_novo):
        # Estratégia simplificada: prioriza o conteúdo novo
        return conteudo_novo