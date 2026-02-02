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

VALID_AGENT_TYPES = ['processador']

class StartAnalysisPayload(BaseModel):
    repository_type: Literal['github', 'gitlab', 'azure']
    repo_name: str = Field(..., description="Nome do repositório (ex: org/projeto/repo)")
    branch_name: str = Field(..., description="Nome da branch para análise")
    agent_type: Literal['processador'] = Field(..., description="Tipo de agente a ser executado (apenas 'processador' permitido)")
    arquivos_especificos: Optional[List[str]] = None
    instrucoes_extras: Optional[str] = None

    @validator('agent_type')
    def validate_agent_type(cls, v):
        if v not in VALID_AGENT_TYPES:
            raise ValueError(f"Tipo de agente inválido: {v}. Apenas 'processador' é permitido.")
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
