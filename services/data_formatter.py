from typing import Dict, Any
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from services.change_consolidator_service import ChangeConsolidatorService

class DataFormatter:
    def __init__(self, changeset_filler=None):
        self.changeset_filler = changeset_filler

    def format_incremental_result_for_commit(self, final_result: Dict[str, Any]) -> Dict[str, Any]:
        resumo_geral = final_result.get("resumo_geral", "")
        conjunto_de_mudancas = final_result.get("conjunto_de_mudancas", [])
        conjunto_de_mudancas = ChangeConsolidatorService.consolidate_changes(conjunto_de_mudancas)
        branch_sugerida_raw = resumo_geral[:50] if resumo_geral else "refatoracao-incremental"
        branch_sugerida = BranchNameSanitizer.sanitize(branch_sugerida_raw)
        titulo_pr = resumo_geral[:72] if resumo_geral else "Refatoração incremental"
        grupo = {
            "branch_sugerida": branch_sugerida,
            "titulo_pr": titulo_pr,
            "resumo_do_pr": resumo_geral if resumo_geral else "Refatoração incremental gerada automaticamente.",
            "conjunto_de_mudancas": conjunto_de_mudancas
        }
        return {
            "resumo_geral": resumo_geral,
            "grupos": [grupo]
        }