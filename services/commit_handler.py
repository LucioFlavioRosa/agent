class CommitHandler:
    def execute_commits(self, job_id, job_info, dados_finais_formatados, repository_type, repo_name):
        grupos = dados_finais_formatados.get("grupos", [])
        if not grupos or all(not grupo.get("conjunto_de_mudancas") for grupo in grupos):
            raise ValueError(f"Tentativa de commit sem mudanças válidas. Verifique a saída do agente e a formatação dos dados. dados_finais_formatados={dados_finais_formatados}")
        # ... restante da implementação original ...
        return {}
