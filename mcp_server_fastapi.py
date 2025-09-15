import json
import uuid
import time
import traceback

from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService

class JobStatus:
    STARTING = 'starting'
    PENDING_APPROVAL = 'pending_approval'
    WORKFLOW_STARTED = 'workflow_started'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REJECTED = 'rejected'

class JobFields:
    STATUS = 'status'
    DATA = 'data'
    ERROR_DETAILS = 'error_details'
    REPO_NAME = 'repo_name'
    ORIGINAL_REPO_NAME = 'original_repo_name'
    PROJETO = 'projeto'
    BRANCH_NAME = 'branch_name'
    ORIGINAL_ANALYSIS_TYPE = 'original_analysis_type'
    INSTRUCOES_EXTRAS = 'instrucoes_extras'
    MODEL_NAME = 'model_name'
    USAR_RAG = 'usar_rag'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    GERAR_NOVO_RELATORIO = 'gerar_novo_relatorio'
    ARQUIVOS_ESPECIFICOS = 'arquivos_especificos'
    ANALYSIS_NAME = 'analysis_name'
    REPOSITORY_TYPE = 'repository_type'
    ANALYSIS_REPORT = 'analysis_report'
    REPORT_BLOB_URL = 'report_blob_url'
    COMMIT_DETAILS = 'commit_details'
    DIAGNOSTIC_LOGS = 'diagnostic_logs'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    PAUSED_AT_STEP = 'paused_at_step'
    SUCCESS = 'success'
    PR_URL = 'pr_url'
    ARQUIVOS_MODIFICADOS = 'arquivos_modificados'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

container = DependencyContainer()
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()

class StartAnalysisPayload(BaseModel):
    repo_name: str
    projeto: str = Field(description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    gerar_novo_relatorio: bool = Field(True, description="Se False, tenta ler relatório existente do Blob Storage usando analysis_name")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")

class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    instrucoes_extras: Optional[str] = None

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = Field(None)
    error_details: Optional[str] = Field(None)
    analysis_report: Optional[str] = Field(None)
    diagnostic_logs: Optional[Dict[str, Any]] = Field(None)
    report_blob_url: Optional[str] = Field(None)

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

class AnalysisByNameResponse(BaseModel):
    job_id: str
    analysis_name: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

def _validate_and_normalize_gitlab_repo_name(repo_name: str) -> str:
    repo_name = repo_name.strip()

    try:
        project_id = int(repo_name)
        print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
        return str(project_id)
    except ValueError:
        pass

    if '/' in repo_name:
        parts = repo_name.split('/')
        if len(parts) >= 2:
            print(f"GitLab path completo detectado: {repo_name}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
            return repo_name
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
            )

    raise HTTPException(
        status_code=400,
        detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
    )

def _normalize_repo_name_by_type(repo_name: str, repository_type: str) -> str:
    if repository_type == 'gitlab':
        normalized = _validate_and_normalize_gitlab_repo_name(repo_name)
        print(f"GitLab - Repo original: '{repo_name}', normalizado: '{normalized}'")
        return normalized
    return repo_name

def _generate_analysis_name(provided_name: Optional[str], job_id: str) -> str:
    if provided_name:
        return provided_name

    analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
    print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
    return analysis_name

def _create_initial_job_data(payload: StartAnalysisPayload, normalized_repo_name: str, analysis_name: str) -> dict:
    return {
        JobFields.STATUS: JobStatus.STARTING,
        JobFields.DATA: {
            JobFields.REPO_NAME: normalized_repo_name,
            JobFields.ORIGINAL_REPO_NAME: payload.repo_name,
            JobFields.PROJETO: payload.projeto,
            JobFields.BRANCH_NAME: payload.branch_name,
            JobFields.ORIGINAL_ANALYSIS_TYPE: payload.analysis_type.value,
            JobFields.INSTRUCOES_EXTRAS: payload.instrucoes_extras,
            JobFields.MODEL_NAME: payload.model_name,
            JobFields.USAR_RAG: payload.usar_rag,
            JobFields.GERAR_RELATORIO_APENAS: payload.gerar_relatorio_apenas,
            JobFields.GERAR_NOVO_RELATORIO: payload.gerar_novo_relatorio,
            JobFields.ARQUIVOS_ESPECIFICOS: payload.arquivos_especificos,
            JobFields.ANALYSIS_NAME: analysis_name,
            JobFields.REPOSITORY_TYPE: payload.repository_type
        },
        JobFields.ERROR_DETAILS: None
    }

def _validate_job_for_approval(job: dict, job_id: str) -> None:
    if not job or job.get(JobFields.STATUS) != JobStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Job não encontrado ou não está aguardando aprovação.")

def _validate_job_exists(job: dict, job_id: str) -> None:
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

def _validate_analysis_exists(analysis_name: str, analysis_service) -> str:
    job_id = analysis_service.find_job_by_analysis_name(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    return job_id

def _get_report_from_job(job: dict, job_id: str) -> str:
    report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
    if not report:
        if job_id:
            raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get(JobFields.STATUS)}")
        else:
            raise HTTPException(status_code=404, detail="Relatório não encontrado no job original")
    return report

def _create_derived_job_data(original_job: dict, analysis_name: str, normalized_repo_name: str, report: str) -> dict:
    original_data = original_job[JobFields.DATA]
    return {
        JobFields.STATUS: JobStatus.STARTING,
        JobFields.DATA: {
            JobFields.REPO_NAME: normalized_repo_name,
            JobFields.ORIGINAL_REPO_NAME: original_data[JobFields.REPO_NAME],
            JobFields.PROJETO: original_data[JobFields.PROJETO],
            JobFields.BRANCH_NAME: original_data[JobFields.BRANCH_NAME],
            JobFields.ORIGINAL_ANALYSIS_TYPE: 'implementacao',
            JobFields.INSTRUCOES_EXTRAS: f"Gerar código baseado no seguinte relatório:\n\n{report}",
            JobFields.MODEL_NAME: original_data.get(JobFields.MODEL_NAME),
            JobFields.USAR_RAG: original_data.get(JobFields.USAR_RAG, False),
            JobFields.GERAR_RELATORIO_APENAS: False,
            JobFields.GERAR_NOVO_RELATORIO: True,
            JobFields.ARQUIVOS_ESPECIFICOS: original_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
            JobFields.ANALYSIS_NAME: f"{analysis_name}-implementation",
            JobFields.REPOSITORY_TYPE: original_data[JobFields.REPOSITORY_TYPE]
        },
        JobFields.ERROR_DETAILS: None
    }

def _build_completed_response(job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
    job_data = job.get(JobFields.DATA, {})
    
    print(f"[{job_id}] Construindo resposta final - gerar_relatorio_apenas: {job_data.get(JobFields.GERAR_RELATORIO_APENAS)}")
    
    if job_data.get(JobFields.GERAR_RELATORIO_APENAS) is True:
        print(f"[{job_id}] Modo relatório apenas - retornando resposta simples")
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            analysis_report=job_data.get(JobFields.ANALYSIS_REPORT),
            report_blob_url=blob_url
        )
    else:
        summary_list = []
        
        commit_details = job_data.get(JobFields.COMMIT_DETAILS, [])
        print(f"[{job_id}] Buscando PRs em commit_details: {len(commit_details)} itens encontrados")
        
        for pr_info in commit_details:
            if pr_info.get(JobFields.SUCCESS) and pr_info.get(JobFields.PR_URL):
                summary_list.append(
                    PullRequestSummary(
                        pull_request_url=pr_info.get(JobFields.PR_URL),
                        branch_name=pr_info.get(JobFields.BRANCH_NAME),
                        arquivos_modificados=pr_info.get(JobFields.ARQUIVOS_MODIFICADOS, [])
                    )
                )
        
        if not summary_list:
            print(f"[{job_id}] Nenhum PR encontrado em commit_details, buscando em diagnostic_logs")
            diagnostic_logs = job_data.get(JobFields.DIAGNOSTIC_LOGS, {})
            
            final_result = diagnostic_logs.get('final_result', {})
            if final_result:
                print(f"[{job_id}] Analisando final_result em diagnostic_logs")
                for key, value in final_result.items():
                    if key.startswith('pr_grupo_') and isinstance(value, dict):
                        print(f"[{job_id}] Encontrado grupo de PR: {key}")
                        branch_name = value.get('resumo_do_pr', key.replace('pr_grupo_', 'branch-'))
                        arquivos_modificados = []
                        
                        conjunto_mudancas = value.get('conjunto_de_mudancas', [])
                        for mudanca in conjunto_mudancas:
                            if mudanca.get('caminho_do_arquivo'):
                                arquivos_modificados.append(mudanca['caminho_do_arquivo'])
                        
                        pr_url = f"PR criado para branch: {branch_name}"
                        
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=pr_url,
                                branch_name=branch_name,
                                arquivos_modificados=arquivos_modificados
                            )
                        )
            
            if not summary_list:
                penultimate_result = diagnostic_logs.get('penultimate_result', {})
                if penultimate_result and isinstance(penultimate_result, dict):
                    print(f"[{job_id}] Analisando penultimate_result em diagnostic_logs")
                    conjunto_mudancas = penultimate_result.get('conjunto_de_mudancas', [])
                    if conjunto_mudancas:
                        arquivos_modificados = []
                        for mudanca in conjunto_mudancas:
                            if mudanca.get('caminho_do_arquivo'):
                                arquivos_modificados.append(mudanca['caminho_do_arquivo'])
                        
                        if arquivos_modificados:
                            summary_list.append(
                                PullRequestSummary(
                                    pull_request_url="PR criado com base no resultado da análise",
                                    branch_name="branch-implementacao",
                                    arquivos_modificados=arquivos_modificados
                                )
                            )
        
        if not blob_url:
            blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
            print(f"[{job_id}] URL do blob extraída do job_data: {blob_url}")
        
        print(f"[{job_id}] Resposta final construída - PRs encontrados: {len(summary_list)}, URL do blob: {blob_url}")
        
        logs = job_data.get(JobFields.DIAGNOSTIC_LOGS)
        return FinalStatusResponse(
            job_id=job_id, 
            status=JobStatus.COMPLETED, 
            summary=summary_list,
            diagnostic_logs=logs,
            report_blob_url=blob_url
        )

app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA.",
    version="9.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator = container.get_workflow_orchestrator()
    workflow_orchestrator.execute_workflow(job_id, start_from_step)

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    
    normalized_repo_name = _normalize_repo_name_by_type(payload.repo_name, payload.repository_type)

    job_id = str(uuid.uuid4())
    analysis_name = _generate_analysis_name(payload.analysis_name, job_id)

    initial_job_data = _create_initial_job_data(payload, normalized_repo_name, analysis_name)

    job_store.set_job(job_id, initial_job_data)

    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)

    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")

    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)

    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    
    job = job_store.get_job(payload.job_id)
    _validate_job_for_approval(job, payload.job_id)

    if payload.action == JobActions.APPROVE:
        if payload.instrucoes_extras:
            job[JobFields.DATA][JobFields.INSTRUCOES_EXTRAS_APROVACAO] = payload.instrucoes_extras
            print(f"[{payload.job_id}] Instruções extras de aprovação salvas: {payload.instrucoes_extras[:100]}...")
        
        job[JobFields.STATUS] = JobStatus.WORKFLOW_STARTED

        paused_step = job[JobFields.DATA].get(JobFields.PAUSED_AT_STEP, 0)
        start_from_step = paused_step + 1

        job_store.set_job(payload.job_id, job)

        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)

        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.WORKFLOW_STARTED, "message": "Aprovação recebida."}

    if payload.action == JobActions.REJECT:
        job[JobFields.STATUS] = JobStatus.REJECTED
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.REJECTED, "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job_store = container.get_job_store()
    
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)

    report = _get_report_from_job(job, job_id)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)

    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)

@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    
    job_id = _validate_analysis_exists(analysis_name, analysis_service)

    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)

    report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)

    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=report,
        report_blob_url=blob_url
    )

@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    
    job_id = _validate_analysis_exists(analysis_name, analysis_service)

    original_job = job_store.get_job(job_id)
    _validate_job_exists(original_job, job_id)

    report = _get_report_from_job(original_job, None)

    original_data = original_job[JobFields.DATA]
    original_repo_name = original_data[JobFields.REPO_NAME]
    original_repository_type = original_data[JobFields.REPOSITORY_TYPE]

    normalized_repo_name = _normalize_repo_name_by_type(original_repo_name, original_repository_type)

    new_job_id = str(uuid.uuid4())

    new_job_data = _create_derived_job_data(original_job, analysis_name, normalized_repo_name, report)

    job_store.set_job(new_job_id, new_job_data)
    analysis_service.register_analysis(f"{analysis_name}-implementation", new_job_id)

    print(f"[{new_job_id}] Job derivado criado - Repositório: '{normalized_repo_name}' (tipo: {original_repository_type}), Projeto: '{original_data[JobFields.PROJETO]}'")

    background_tasks.add_task(run_workflow_task, new_job_id, start_from_step=0)

    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job_store = container.get_job_store()
    
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)

    status = job.get(JobFields.STATUS)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)

    try:
        if status == JobStatus.COMPLETED:
            return _build_completed_response(job_id, job, blob_url)
        elif status == JobStatus.FAILED:
            logs = job.get(JobFields.DATA, {}).get(JobFields.DIAGNOSTIC_LOGS)
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get(JobFields.ERROR_DETAILS, "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs,
                report_blob_url=blob_url
            )
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")