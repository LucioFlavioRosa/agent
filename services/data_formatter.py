from typing import Dict, Any

class DataFormatter:
    def __init__(self, changeset_filler=None):
        self.changeset_filler = changeset_filler

    def format_incremental_result_for_commit(self, final_result: Dict[str, Any]) -> Dict[str, Any]:
        resumo_geral = final_result.get("resumo_geral", "")
        conjunto_de_mudancas = final_result.get("conjunto_de_mudancas", [])
        grupo = {
            "branch_sugerida": resumo_geral[:50] if resumo_geral else "refatoracao-incremental",
            "titulo_pr": resumo_geral[:72] if resumo_geral else "Refatoração incremental",
            "resumo_do_pr": resumo_geral if resumo_geral else "Refatoração incremental gerada automaticamente.",
            "conjunto_de_mudancas": conjunto_de_mudancas
        }
        return {
            "resumo_geral": resumo_geral,
            "grupos": [grupo]
        }
