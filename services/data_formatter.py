from tools.repo_committers.path_validator import PathValidator

class DataFormatter:
    def __init__(self, changeset_filler):
        self.changeset_filler = changeset_filler

    def format_data(self, job_id, conjunto_de_mudancas):
        mudancas_validas = []
        mudancas_invalidas = []
        for idx, mudanca in enumerate(conjunto_de_mudancas):
            # Normalização de chaves de caminho (passo 1 do relatório)
            caminho = None
            if 'caminho' in mudanca:
                caminho = mudanca['caminho']
            elif 'caminho_do_arquivo' in mudanca:
                caminho = mudanca['caminho_do_arquivo']
                mudanca['caminho'] = caminho
            elif 'path' in mudanca:
                caminho = mudanca['path']
                mudanca['caminho'] = caminho
            else:
                caminho = None
                mudanca['caminho'] = None
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
        if isinstance(final_result, dict) and 'grupos' in final_result and isinstance(final_result['grupos'], list):
            # Normalização de chaves de caminho para todos os grupos (passo 1)
            for grupo in final_result['grupos']:
                if 'conjunto_de_mudancas' in grupo and isinstance(grupo['conjunto_de_mudancas'], list):
                    for mudanca in grupo['conjunto_de_mudancas']:
                        if 'caminho' not in mudanca:
                            if 'caminho_do_arquivo' in mudanca:
                                mudanca['caminho'] = mudanca['caminho_do_arquivo']
                            elif 'path' in mudanca:
                                mudanca['caminho'] = mudanca['path']
            return final_result
        conjunto_de_mudancas = final_result.get("conjunto_de_mudancas", [])
        if not conjunto_de_mudancas:
            print("[AVISO][DataFormatter][format_incremental_result_for_commit] conjunto_de_mudancas está vazio após consolidação. Será gerada estrutura com grupos como lista vazia.")
            return {"grupos": []}
        # Normalização de chaves de caminho (passo 1)
        for mudanca in conjunto_de_mudancas:
            if 'caminho' not in mudanca:
                if 'caminho_do_arquivo' in mudanca:
                    mudanca['caminho'] = mudanca['caminho_do_arquivo']
                elif 'path' in mudanca:
                    mudanca['caminho'] = mudanca['path']
        grupo = {
            "titulo_pr": final_result.get("resumo_geral", "Implementação incremental"),
            "resumo_do_pr": final_result.get("resumo_geral", "Implementação incremental"),
            "branch_sugerida": "implementacao-incremental",
            "conjunto_de_mudancas": conjunto_de_mudancas
        }
        return {"grupos": [grupo]}
