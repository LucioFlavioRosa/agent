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

# ... (classes pydantic e funções auxiliares mantidas)

# ... (demais funções auxiliares mantidas)

def _build_completed_response(job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
    job_data = job.get(JobFields.DATA, {})
    print(f"[DEBUG] _build_completed_response: job_id={job_id}, gerar_relatorio_apenas={job_data.get(JobFields.GERAR_RELATORIO_APENAS)}, tamanho analysis_report={len(job_data.get(JobFields.ANALYSIS_REPORT, '') if job_data.get(JobFields.ANALYSIS_REPORT) else 0)}, report_blob_url={blob_url}")
    if job_data.get(JobFields.GERAR_RELATORIO_APENAS) is True:
        print(f"[{job_id}] Resposta para modo report_only - Blob URL: {blob_url}")
        print(f"[{job_id}] Tamanho do relatório: {len(job_data.get(JobFields.ANALYSIS_REPORT, ''))} chars")
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            analysis_report=job_data.get(JobFields.ANALYSIS_REPORT),
            report_blob_url=blob_url
        )
    else:
        summary_list = []
        commit_details = job_data.get(JobFields.COMMIT_DETAILS, [])
        print(f"[{job_id}] DIAGNÓSTICO - commit_details lido do job: {commit_details}")
        print(f"[{job_id}] DIAGNÓSTICO - Buscando PRs em commit_details: {len(commit_details)} itens encontrados")
        for i, pr_info in enumerate(commit_details):
            if isinstance(pr_info, dict):
                pr_url = pr_info.get('pr_url')
                branch_name = pr_info.get('branch_name')
                arquivos_modificados = pr_info.get('arquivos_modificados', [])
                success = pr_info.get('success', False)
                print(f"[{job_id}] DIAGNÓSTICO - PR {i+1}: pr_url='{pr_url}', branch_name='{branch_name}', success={success}, arquivos={len(arquivos_modificados)}")
                if success and branch_name:
                    if pr_url:
                        print(f"[{job_id}] PR válido encontrado: {pr_url} - Branch: {branch_name} - Arquivos: {len(arquivos_modificados)}")
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=pr_url,
                                branch_name=branch_name,
                                arquivos_modificados=arquivos_modificados
                            )
                        )
                    else:
                        print(f"[{job_id}] Branch processada sem PR URL: {branch_name} - Arquivos: {len(arquivos_modificados)}")
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=f"Branch processada: {branch_name}",
                                branch_name=branch_name,
                                arquivos_modificados=arquivos_modificados
                            )
                        )
                elif pr_info.get('message') and branch_name:
                    print(f"[{job_id}] Branch processada: {branch_name} - Arquivos: {len(arquivos_modificados)}")
                    summary_list.append(
                        PullRequestSummary(
                            pull_request_url=pr_info.get('message', f"Branch processada: {branch_name}"),
                            branch_name=branch_name,
                            arquivos_modificados=arquivos_modificados
                        )
                    )
                else:
                    print(f"[{job_id}] AVISO - PR {i+1} não atende critérios: success={success}, pr_url='{pr_url}', branch_name='{branch_name}'")
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
        print(f"[{job_id}] DIAGNÓSTICO FINAL - PRs encontrados: {len(summary_list)}, URL do blob: {blob_url}")
        for i, pr_summary in enumerate(summary_list):
            print(f"[{job_id}] DIAGNÓSTICO FINAL - PR {i+1}: url='{pr_summary.pull_request_url}', branch='{pr_summary.branch_name}', arquivos={len(pr_summary.arquivos_modificados)}")
        logs = job_data.get(JobFields.DIAGNOSTIC_LOGS)
        blob_filename = _extract_blob_filename(blob_url)
        log_custom_data(
            job_id=job_id,
            projeto=job_data.get(JobFields.PROJETO),
            data_hora=time.strftime('%Y-%m-%d %H:%M:%S'),
            status=JobStatus.COMPLETED,
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
        for pr_summary in summary_list:
            log_custom_data(
                job_id=job_id,
                projeto=job_data.get(JobFields.PROJETO),
                data_hora=time.strftime('%Y-%m-%d %H:%M:%S'),
                status=JobStatus.COMPLETED,
                tipo_repositorio=job_data.get(JobFields.REPOSITORY_TYPE),
                nome_repositorio=job_data.get(JobFields.REPO_NAME),
                tipo_analise=job_data.get(JobFields.ORIGINAL_ANALYSIS_TYPE),
                branch_name=job_data.get(JobFields.BRANCH_NAME_MODERNIZADO),
                analysis_name=job_data.get(JobFields.ANALYSIS_NAME),
                arquivos_especificos=job_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
                pr_url=pr_summary.pull_request_url,
                arquivos_modificados=pr_summary.arquivos_modificados,
                retornar_lista_arquivos=job_data.get(JobFields.RETORNAR_LISTA_ARQUIVOS),
                modo_adicao_incremental=job_data.get(JobFields.MODO_ADICAO_INCREMENTAL),
                usuario_executor=job_data.get(JobFields.USUARIO_EXECUTOR),
                blob_filename=blob_filename
            )
        return FinalStatusResponse(
            job_id=job_id, 
            status=JobStatus.COMPLETED, 
            summary=summary_list,
            diagnostic_logs=logs,
            report_blob_url=blob_url
        )

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)
    status = job.get(JobFields.STATUS)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)
    job_data = job.get(JobFields.DATA, {})
    print(f"[DEBUG] get_status: job_id={job_id}, status={status}, gerar_relatorio_apenas={job_data.get(JobFields.GERAR_RELATORIO_APENAS)}")
    try:
        if status == JobStatus.COMPLETED:
            job_data = job.get(JobFields.DATA, {})
            if job_data.get(JobFields.GERAR_RELATORIO_APENAS) is True:
                print(f"[{job_id}] Resposta para modo report_only - Blob URL: {blob_url}")
                print(f"[{job_id}] Tamanho do relatório: {len(job_data.get(JobFields.ANALYSIS_REPORT, ''))} chars")
            return _build_completed_response(job_id, job, blob_url)
        elif status == JobStatus.FAILED:
            job_data = job.get(JobFields.DATA, {})
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
