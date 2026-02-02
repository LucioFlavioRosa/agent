# Modelos de dados necessários para revisão e melhoria de código via agentes genéricos.
# Todos os modelos/enums relacionados exclusivamente ao AgenteProcessador ou AgenteRevisorCodigo foram removidos/comentados.

# Exemplo de modelo genérico (mantenha apenas o que for necessário para agentes revisor/comparador)
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

# Outros modelos necessários para o fluxo de revisão/melhoria podem ser mantidos abaixo.

# ---
# Modelos relacionados exclusivamente ao AgenteProcessador ou AgenteRevisorCodigo foram removidos.
# ---
