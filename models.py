# Modelos de dados necessários para revisão e melhoria de código via agentes genéricos.
# Todos os modelos/enums relacionados exclusivamente ao AgenteProcessador ou AgenteRevisorCodigo foram removidos/comentados.

from pydantic import BaseModel
from typing import Optional

class JobFields(BaseModel):
    job_id: str
    status: str
    repo_name: Optional[str] = None
    branch_name: Optional[str] = None
    agent_type: Optional[str] = None
    arquivos_especificos: Optional[list] = None
    instrucoes_extras: Optional[str] = None
    analysis_report: Optional[str] = None
    report_blob_url: Optional[str] = None
    projeto: Optional[str] = None
    analysis_name: Optional[str] = None
    gerar_relatorio_apenas: Optional[bool] = None
    retornar_lista_arquivos: Optional[bool] = None
    usuario_executor: Optional[str] = None
    # REMOVIDO: REPO_NAME_MODERNIZADO
    # REMOVIDO: BRANCH_NAME_MODERNIZADO
    # REMOVIDO: EXECUTAR_STEPS_INCREMENTALMENTE

# Outros modelos necessários para o fluxo de revisão/melhoria podem ser mantidos abaixo.

# ---
# Modelos relacionados exclusivamente ao AgenteProcessador ou AgenteRevisorCodigo foram removidos.
# ---
