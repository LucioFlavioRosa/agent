from tools.repo_committers.path_validator import PathValidator

class DataFormatter:
    def __init__(self, changeset_filler):
        self.changeset_filler = changeset_filler

    def format_data(self, job_id, conjunto_de_mudancas):
        mudancas_validas = []
        mudancas_invalidas = []
        for idx, mudanca in enumerate(conjunto_de_mudancas):
            caminho = mudanca.get("caminho")
            try:
                caminho_validado = PathValidator.validate_path(caminho)
                mudanca["caminho"] = caminho_validado
                mudancas_validas.append(mudanca)
            except Exception as e:
                print(f"[ERRO][DataFormatter][format_data] job_id={job_id}, Mudança {idx}: caminho inválido: '{caminho}'. Erro: {e}")
                mudancas_invalidas.append({"indice": idx, "caminho": caminho, "erro": str(e)})
        print(f"[DataFormatter][format_data] job_id={job_id}: {len(mudancas_validas)} mudanças validadas, {len(mudancas_invalidas)} rejeitadas.")
        return mudancas_validas

    def format_incremental_result_for_commit(self, final_result):
        # Se já está no formato esperado (tem 'grupos' que é lista de dicts), retorna direto
        if isinstance(final_result, dict) and 'grupos' in final_result and isinstance(final_result['grupos'], list):
            return final_result
        # Caso contrário, encapsula em um grupo único
        grupo = {
            "titulo_pr": final_result.get("resumo_geral", "Implementação incremental"),
            "resumo_do_pr": final_result.get("resumo_geral", "Implementação incremental"),
            "branch_sugerida": "implementacao-incremental",
            "conjunto_de_mudancas": final_result.get("conjunto_de_mudancas", [])
        }
        return {"grupos": [grupo]}
