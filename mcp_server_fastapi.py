from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from services.simplified_workflow_service import SimplifiedWorkflowService

app = FastAPI(
    title="Code Review & Improvement Server",
    description="API simplificada para revisão e melhoria de código via agentes.",
    version="1.0.0"
)

workflow_service = SimplifiedWorkflowService()

class StartAnalysisPayload(BaseModel):
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(..., description="Tipo do repositório")
    repo_name: str = Field(..., description="Nome do repositório (ex: org/projeto/repo)")
    branch_name: str = Field(..., description="Nome da branch para análise")
    analysis_type: str = Field(..., description="Tipo de análise a ser executada")
    arquivos_especificos: Optional[List[str]] = None
    instrucoes_extras: Optional[str] = None
    projeto: Optional[str] = None
    analysis_name: Optional[str] = None
    gerar_relatorio_apenas: Optional[bool] = None
    retornar_lista_arquivos: Optional[bool] = None
    usuario_executor: str = Field(..., description="Email do usuário executor (obrigatório)")

    @validator('usuario_executor')
    def validate_usuario_executor(cls, v):
        if not v or '@' not in v:
            raise ValueError("usuario_executor deve ser um email válido.")
        return v

class StartAnalysisResponse(BaseModel):
    job_id: str

class StatusResponse(BaseModel):
    job_id: str
    status: str
    report_url: Optional[str] = None
    analysis_report: Optional[str] = None

@app.post("/start-analysis", response_model=StartAnalysisResponse)
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_id = workflow_service.start_analysis(payload)
    background_tasks.add_task(workflow_service.run_analysis, job_id)
    return StartAnalysisResponse(job_id=job_id)

@app.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str):
    status_info = workflow_service.get_status(job_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(**status_info)

@app.get("/report/{job_id}", response_model=StatusResponse)
def get_report(job_id: str):
    report_info = workflow_service.get_report(job_id)
    if not report_info:
        raise HTTPException(status_code=404, detail="Report not found")
    return StatusResponse(**report_info)
