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
