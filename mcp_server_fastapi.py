import json
import uuid
import yaml
import importlib
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do projeto ---
from tools.job_store import set_job, get_job
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Modelos de Dados Pydantic ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["relatorio_analise_de_design_de_codigo", "relatorio_refatoracao_codigo", 
                            "relatorio_documentacao_codigo", "relatorio_avaliacao_terraform"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False, description="Define se a análise deve usar a base de conhecimento RAG.")
    gerar_relatorio_apenas: bool = Field(False, description="Se True, executa apenas a geração do relatório inicial e finaliza.")


class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = Field(None, description="Resumo dos PRs e arquivos modificados.")
    error_details: Optional[str] = Field(None, description="Detalhes do erro, se o job falhou.")
    analysis_report: Optional[str] = Field(None, description="Relatório inicial da IA, se aplicável.")

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]


# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA para análise e refatoração de código.",
    version="8.0.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WORKFLOW_REGISTRY ---
def load_workflow_registry(filepath: str) -> dict:
    """
    Carrega a configuração de workflows de um arquivo YAML e resolve as
    referências de função em string para objetos de função reais.
    """
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for workflow_name, workflow_data in config.items():
        for step in workflow_data.get("steps", []):
            if "agent_function" in step and isinstance(step["agent_function"], str):
                module_path, function_name = step["agent_function"].rsplit(".", 1)
                try:
                    module = importlib.import_module(module_path)
                    function_obj = getattr(module, function_name)
                    step["agent_function"] = function_obj # Substitui a string pela função
                except (ImportError, AttributeError) as e:
                    raise ImportError(
                        f"Não foi possível carregar a função '{step['agent_function']}' "
                        f"definida no workflow '{workflow_name}'. Verifique o caminho. Erro: {e}"
                    )
    print("Workflows carregados e processados com sucesso.")
    return config

# Carrega a configuração na inicialização do servidor
WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")

def handle_task_exception(job_id: str, e: Exception, step: str):
    error_text = str(e)
    error_message = f"Erro fatal durante a etapa '{step}': {error_text}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error_details'] = error_message
            set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        job_info['status'] = 'reading_repository'
        set_job(job_id, job_info)
        print(f"[{job_id}] Etapa 1: Delegando leitura e análise para o agente (RAG: {payload.usar_rag})...")
        
        resposta_agente = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras,
            usar_rag=payload.usar_rag 
        )
        
        full_llm_response_obj = resposta_agente['resultado']['reposta_final']
        report_text_only = full_llm_response_obj['reposta_final']

        # [ALTERADO] A lógica agora depende da nova flag
        # Se for apenas para gerar o relatório, o processo já termina aqui.
        if payload.gerar_relatorio_apenas:
            job_info['status'] = 'completed'
            job_info['data']['analysis_report'] = report_text_only
            print(f"[{job_id}] Relatório gerado com sucesso. Processo finalizado conforme solicitado (gerar_relatorio_apenas=True).")
        else:
            job_info['status'] = 'pending_approval'
            job_info['data']['analysis_report'] = report_text_only
            print(f"[{job_id}] Relatório gerado com sucesso. Job aguardando aprovação.")
        
        # Armazena as decisões para os próximos passos (se houver)
        job_info['data']['usar_rag'] = payload.usar_rag
        job_info['data']['gerar_relatorio_apenas'] = payload.gerar_relatorio_apenas
        
        set_job(job_id, job_info)
        
    except Exception as e:
        current_step = job_info.get('status', 'report_generation') if job_info else 'report_generation'
        handle_task_exception(job_id, e, current_step)

def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início do workflow.")
        
        print(f"[{job_id}] Iniciando workflow completo após aprovação...")
        
        usar_rag = job_info.get("data", {}).get("usar_rag", False)
        print(f"[{job_id}] Executando workflow com RAG: {usar_rag}")

        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update'] 
            set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            
            agent_params = step['params'].copy()
            agent_params['usar_rag'] = usar_rag
            
            if i == 0:
                relatorio_gerado = job_info['data']['analysis_report']
                instrucoes_iniciais = job_info['data'].get('instrucoes_extras')
                observacoes_aprovacao = job_info['data'].get('observacoes_aprovacao')
                instrucoes_completas = relatorio_gerado
                if instrucoes_iniciais:
                    instrucoes_completas += f"\n\n--- INSTRUÇÕES ADICIONAIS DO USUÁRIO (INICIAL) ---\n{instrucoes_iniciais}"
                if observacoes_aprovacao:
                    instrucoes_completas += f"\n\n--- OBSERVAÇÕES DA APROVAÇÃO (APLICAR COM PRIORIDADE) ---\n{observacoes_aprovacao}"
                
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': instrucoes_completas
                })
            else:
                lightweight_changeset = {
                    "resumo_geral": previous_step_result.get("resumo_geral"),
                    "conjunto_de_mudancas": [
                        {
                            "caminho_do_arquivo": mudanca.get("caminho_do_arquivo"),
                            "justificativa": mudanca.get("justificativa")
                        }
                        for mudanca in previous_step_result.get("conjunto_de_mudancas", [])
                    ]
                }
                agent_params['codigo'] = json.dumps(lightweight_changeset, indent=2, ensure_ascii=False)
            
            agent_response = step['agent_function'](**agent_params)
            
            full_llm_response_obj = agent_response['resultado']['reposta_final']
            json_string_from_llm = full_llm_response_obj.get('reposta_final', '')

            if not json_string_from_llm or not json_string_from_llm.strip():
                raise ValueError(f"A IA retornou uma resposta vazia para a etapa '{job_info['status']}'.")

            cleaned_json_string = json_string_from_llm.replace("```json", "").replace("```", "").strip()
            previous_step_result = json.loads(cleaned_json_string)

            if i == 0:
                job_info['data']['resultado_refatoracao'] = previous_step_result
            else:
                job_info['data']['resultado_agrupamento'] = previous_step_result
            set_job(job_id, job_info)
        
        job_info['status'] = 'populating_data'
        set_job(job_id, job_info)
        
        dados_preenchidos = preenchimento.main(
            json_agrupado=job_info['data']['resultado_agrupamento'],
            json_inicial=job_info['data']['resultado_refatoracao']
        )
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        set_job(job_id, job_info)
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(nome_repo=job_info['data']['repo_name'], dados_agrupados=dados_finais_formatados)
        
        job_info['data']['commit_details'] = commit_results
        job_info['status'] = 'completed'
        set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")

    except Exception as e:
        current_step = job_info.get('status', 'run_workflow') if job_info else 'run_workflow'
        handle_task_exception(job_id, e, current_step)
# --- Endpoints da API ---

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    # ... (código inalterado)
    job_id = str(uuid.uuid4())
    initial_job_data = {
        'status': 'starting',
        'data': {
            'repo_name': payload.repo_name,
            'branch_name': payload.branch_name,
            'original_analysis_type': payload.analysis_type,
            'instrucoes_extras': payload.instrucoes_extras,
        },
        'error_details': None
    }
    set_job(job_id, initial_job_data)
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    # Esta validação agora é mais flexível, pois um job pode ter sido concluído antes
    if job['status'] not in ['pending_approval']:
        # Se já foi concluído (porque era só relatório), retorna uma mensagem amigável
        if job['status'] == 'completed':
            return {"job_id": payload.job_id, "status": "completed", "message": "Este job já foi concluído (modo apenas relatório)."}
        raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        
        job['status'] = 'workflow_started'
        set_job(payload.job_id, job)
        
        # Inicia o workflow completo em background
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida. Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    """
    Endpoint dedicado para buscar o conteúdo do relatório de análise.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    if job.get('status') != 'pending_approval':
        raise HTTPException(status_code=400, detail=f"O relatório só está disponível quando o status é 'pending_approval'. Status atual: {job.get('status')}")

    return ReportResponse(
        job_id=job_id,
        analysis_report=job.get("data", {}).get("analysis_report")
    )

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"]) 
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Verifica o status de um job. Retorna um resumo inteligente dependendo
    do estado e do tipo de execução do job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    
    try:
        # Caso 1: Job concluído com sucesso
        if status == 'completed':
            # [LÓGICA APRIMORADA]
            # Verifica se o job foi executado no modo "apenas relatório".
            if job.get("data", {}).get("gerar_relatorio_apenas") is True:
                # Se sim, o resultado principal é o próprio relatório.
                return FinalStatusResponse(
                    job_id=job_id,
                    status=status,
                    analysis_report=job.get("data", {}).get("analysis_report")
                )
            else:
                # Se não, foi um workflow completo, então monta o resumo dos PRs.
                summary_list = []
                commit_details = job.get("data", {}).get("commit_details", [])
                dados_agrupados = job.get("data", {}).get("resultado_agrupamento", {})

                mapa_arquivos_por_branch = {}
                for nome_grupo, detalhes_grupo in dados_agrupados.items():
                    if isinstance(detalhes_grupo, dict) and 'conjunto_de_mudancas' in detalhes_grupo:
                        arquivos = [m.get("caminho_do_arquivo") for m in detalhes_grupo.get("conjunto_de_mudancas", []) if m]
                        mapa_arquivos_por_branch[nome_grupo] = arquivos

                for pr_info in commit_details:
                    branch_name = pr_info.get("branch_name")
                    if pr_info.get("success") and pr_info.get("pr_url"):
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=pr_info.get("pr_url"),
                                branch_name=branch_name,
                                arquivos_modificados=mapa_arquivos_por_branch.get(branch_name, [])
                            )
                        )
                
                return FinalStatusResponse(
                    job_id=job_id,
                    status=status,
                    summary=summary_list
                )

        # Caso 2: Job falhou
        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado.")
            )
        
        # Caso 3: Job em andamento
        else:
            return FinalStatusResponse(
                job_id=job_id,
                status=status
            )

    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")
