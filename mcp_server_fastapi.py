import json
import uuid
import time
import traceback
import os
from urllib.parse import urlparse

from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService
from agents.logging_utils import log_custom_data
from models import JobStatus, JobFields, JobActions

container = DependencyContainer()
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()

class StartAnalysisPayload(BaseModel):
    repo_name_modernizado: str = Field(description="Nome do repositório modernizado")
    branch_name_modernizado: Optional[str] = Field(None, description="Branch do repositório modernizado")
    projeto: str = Field(description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    gerar_novo_relatorio: bool = Field(True, description="Se False, tenta ler relatório existente do Blob Storage usando analysis_name")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")
    repo_name_original: Optional[str] = Field(None, description="Nome do repositório original para comparação")
    branch_name_original: Optional[str] = Field(None, description="Branch do repositório original")
    retornar_lista_arquivos: bool = Field(False, description="Se True, além do código filtrado, retorna lista completa de todos os arquivos do repositório")
    modo_adicao_incremental: bool = Field(False, description="Se True, o novo conteúdo será ADICIONADO ao final dos arquivos existentes, ao invés de substituí-los. Útil para migrações de frameworks.")
    usuario_executor: Optional[str] = Field(None, description="Nome do usuário que está executando a análise")

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
        parts = [p for p in repo_name.split('/') if p]

        if len(parts) >= 2:
            normalized_path = '/'.join(parts)
            print(f"GitLab path completo detectado: {normalized_path}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
            return normalized_path
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
            JobFields.ORIGINAL_REPO_NAME: payload.repo_name_modernizado,
            JobFields.PROJETO: payload.projeto,
            JobFields.BRANCH_NAME: payload.branch_name_modernizado,
            JobFields.ORIGINAL_ANALYSIS_TYPE: payload.analysis_type.value,
            JobFields.INSTRUCOES_EXTRAS: payload.instrucoes_extras,
            JobFields.MODEL_NAME: payload.model_name,
            JobFields.USAR_RAG: payload.usar_rag,
            JobFields.GERAR_RELATORIO_APENAS: payload.gerar_relatorio_apenas,
            JobFields.GERAR_NOVO_RELATORIO: payload.gerar_novo_relatorio,
            JobFields.ARQUIVOS_ESPECIFICOS: payload.arquivos_especificos,
            JobFields.ANALYSIS_NAME: analysis_name,
            JobFields.REPOSITORY_TYPE: payload.repository_type,
            JobFields.REPO_NAME_MODERNIZADO: payload.repo_name_modernizado,
            JobFields.BRANCH_NAME_MODERNIZADO: payload.branch_name_modernizado,
            JobFields.REPO_NAME_ORIGINAL: payload.repo_name_original,
            JobFields.BRANCH_NAME_ORIGINAL: payload.branch_name_original,
            JobFields.RETORNAR_LISTA_ARQUIVOS: payload.retornar_lista_arquivos,
            JobFields.MODO_ADICAO_INCREMENTAL: payload.modo_adicao_incremental,
            JobFields.USUARIO_EXECUTOR: payload.usuario_executor
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

# Passo 3: Modificar _get_report_from_job para fallback ao blob storage
from tools.blob_report_reader import read_report_from_blob

def _get_report_from_job(job: dict, job_id: str) -> str:
    report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
    status = job.get(JobFields.STATUS)
    job_data = job.get(JobFields.DATA, {})
    gerar_relatorio_apenas = job_data.get(JobFields.GERAR_RELATORIO_APENAS, False)
    blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
    projeto = job_data.get(JobFields.PROJETO)
    analysis_type = job_data.get(JobFields.ORIGINAL_ANALYSIS_TYPE)
    repository_type = job_data.get(JobFields.REPOSITORY_TYPE)
    repo_name = job_data.get(JobFields.REPO_NAME)
    branch_name = job_data.get(JobFields.BRANCH_NAME)
    analysis_name = job_data.get(JobFields.ANALYSIS_NAME)

    if report:
        return report
    # Fallback: completed + gerar_relatorio_apenas, tenta blob storage
    if status == JobStatus.COMPLETED and gerar_relatorio_apenas:
        print(f"[{job_id}] [get_report_from_job] Fallback: tentando ler relatório do blob storage pois analysis_report está vazio.")
        if blob_url:
            try:
                # Tenta ler diretamente do blob_url se possível (mas normalmente precisa dos metadados)
                blob_report = read_report_from_blob(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
                if blob_report:
                    print(f"[{job_id}] [get_report_from_job] Sucesso no fallback: relatório lido do blob storage, tamanho={len(blob_report)}")
                    return blob_report
            except Exception as e:
                print(f"[{job_id}] [get_report_from_job] Erro ao tentar ler relatório do blob storage: {e}")
        else:
            print(f"[{job_id}] [get_report_from_job] Não há blob_url, tentando ler do blob storage por metadados.")
            try:
                blob_report = read_report_from_blob(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
                if blob_report:
                    print(f"[{job_id}] [get_report_from_job] Sucesso no fallback: relatório lido do blob storage por metadados, tamanho={len(blob_report)}")
                    return blob_report
            except Exception as e:
                print(f"[{job_id}] [get_report_from_job] Erro ao tentar ler relatório do blob storage por metadados: {e}")
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {status}")
    if not report:
        if job_id:
            raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get(JobFields.STATUS)}")
        else:
            raise HTTPException(status_code=404, detail="Relatório não encontrado no job original")
    return report

# Passo 4: Adicionar logs detalhados em get_job_report
@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    status = job.get('status')
    analysis_report = job.get('data', {}).get('analysis_report', '')
    blob_url = job.get('data', {}).get('report_blob_url')
    gerar_relatorio_apenas = job.get('data', {}).get('gerar_relatorio_apenas')
    print(f"[{job_id}] [get_job_report] status={status}, report_size={len(analysis_report)}, blob_url={blob_url}, report_only={gerar_relatorio_apenas}")
    _validate_job_exists(job, job_id)
    report = _get_report_from_job(job, job_id)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)

# Demais endpoints permanecem inalterados

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    
    repo_name = payload.repo_name_modernizado
    branch_name = payload.branch_name_modernizado
    
    normalized_repo_name = _normalize_repo_name_by_type(repo_name, payload.repository_type)

    job_id = str(uuid.uuid4())
    analysis_name = _generate_analysis_name(payload.analysis_name, job_id)

    initial_job_data = _create_initial_job_data(payload, normalized_repo_name, analysis_name)

    job_store.set_job(job_id, initial_job_data)

    log_custom_data(
        job_id=job_id,
        projeto=payload.projeto,
        data_hora=time.strftime('%Y-%m-%d %H:%M:%S'),
        status=JobStatus.STARTING,
        tipo_repositorio=payload.repository_type,
        nome_repositorio=normalized_repo_name,
        tipo_analise=payload.analysis_type.value,
        branch_name=payload.branch_name_modernizado,
        analysis_name=analysis_name,
        arquivos_especificos=payload.arquivos_especificos,
        retornar_lista_arquivos=payload.retornar_lista_arquivos,
        modo_adicao_incremental=payload.modo_adicao_incremental,
        usuario_executor=payload.usuario_executor
    )

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
    job_data = job.get(JobFields.DATA, {})
    blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
    gerar_relatorio_apenas = job_data.get(JobFields.GERAR_RELATORIO_APENAS, False)
    analysis_report = job_data.get(JobFields.ANALYSIS_REPORT, None)

    print(f"[{job_id}] [get_status] status: {status}")
    print(f"[{job_id}] [get_status] gerar_relatorio_apenas: {gerar_relatorio_apenas}")
    print(f"[{job_id}] [get_status] Tamanho analysis_report: {len(analysis_report) if analysis_report else 0}")
    print(f"[{job_id}] [get_status] report_blob_url: {blob_url}")
    print(f"[{job_id}] [get_status] ANTES _build_completed_response: gerar_relatorio_apenas={gerar_relatorio_apenas}, analysis_report_size={len(analysis_report) if analysis_report else 0}, blob_url={blob_url}")

    try:
        if status == JobStatus.COMPLETED:
            return _build_completed_response(job_id, job, blob_url)
        elif status == JobStatus.FAILED:
            logs = job_data.get(JobFields.DIAGNOSTIC_LOGS)
            blob_filename = _extract_blob_filename(job_data.get(JobFields.REPORT_BLOB_URL))
            log_custom_data(
                job_id=job_id,
                projeto=job_data.get(JobFields.PROJETO),
                data_hora=time.strftime('%Y-%m-%d %H:%M:%S'),
                status=JobStatus.FAILED,
                tipo_repositorio=job_data.get(JobFields.REPOSITORY_TYPE),
                nome_repositorio=job_data.get(JobFields.REPO_NAME),
                tipo_analise=job_data.get(JobFields.ORIGINAL_ANALYSIS_TYPE),
                branch_name=job_data.get(JobFields.BRANCH_NAME),
                analysis_name=job_data.get(JobFields.ANALYSIS_NAME),
                arquivos_especificos=job_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
                retornar_lista_arquivos=job_data.get(JobFields.RETORNAR_LISTA_ARQUIVOS),
                modo_adicao_incremental=job_data.get(JobFields.MODO_ADICAO_INCREMENTAL),
                usuario_executor=job_data.get(JobFields.USUARIO_EXECUTOR),
                blob_filename=blob_filename
            )
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
