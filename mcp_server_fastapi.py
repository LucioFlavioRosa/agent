# Arquivo: mcp_server_fastapi.py (VERSÃO COMPLETA E FINAL)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict

# [IMPORTANTE] Middleware para permitir a comunicação entre frontend e backend
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do seu projeto ---
# Certifique-se de que estes imports correspondem à sua estrutura de pastas
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Modelos de Dados (Pydantic) ---
class StartJobPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["design", "relatorio_teste_unitario"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None

class StartJobResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    files_read: Optional[List[str]] = None
    analysis_report: Optional[str] = None
    error_details: Optional[str] = None

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor com fluxo de status deliberado para análise de código.",
    version="4.0.0"
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para o domínio do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Armazenamento em memória para os jobs
jobs: Dict[str, Dict] = {} 

# Registro de workflows pós-aprovação
WORKFLOW_REGISTRY = {
    "design": {
        "description": "Analisa o design, refatora o código e agrupa os commits.",
        "steps": [{"status_update": "refactoring_code", "agent_function": agente_revisor.main, "params": {"tipo_analise": "refatoracao"}},
                  {"status_update": "grouping_commits", "agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_design"}}]
    },
    "relatorio_teste_unitario": {
        "description": "Cria testes unitários com base no relatório e os agrupa.",
        "steps": [{"status_update": "writing_unit_tests", "agent_function": agente_revisor.main, "params": {"tipo_analise": "escrever_testes"}},
                  {"status_update": "grouping_tests", "agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_testes"}}]
    }
}

# --- Lógica das Tarefas em Background ---

def run_file_reading_task(job_id: str, payload: StartJobPayload):
    """
    Tarefa 1: Apenas lê os arquivos do repositório e para, aguardando o próximo passo.
    """
    try:
        jobs[job_id]['status'] = 'reading_files'
        print(f"[{job_id}] Tarefa de leitura de arquivos iniciada...")
        
        codigo_com_conteudo = agente_revisor.ler_codigo_do_repositorio(
            repositorio=payload.repo_name,
            tipo_analise=payload.analysis_type,
            nome_branch=payload.branch_name
        )
        nomes_dos_arquivos = list(codigo_com_conteudo.keys())

        # Atualiza o status para um estado de "parada", aguardando o próximo comando
        jobs[job_id]['status'] = 'files_read_awaits_analysis'
        jobs[job_id]['data']['files_read'] = nomes_dos_arquivos
        jobs[job_id]['data']['codigo_com_conteudo'] = codigo_com_conteudo
        jobs[job_id]['data'].update(payload.dict())
        print(f"[{job_id}] Leitura concluída. Aguardando comando para iniciar análise.")

    except Exception as e:
        print(f"ERRO FATAL na tarefa de leitura [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

def run_report_generation_task(job_id: str):
    """
    Tarefa 2: Disparada pelo novo endpoint, apenas gera o relatório da OpenAI.
    """
    try:
        job_info = jobs[job_id]
        job_info['status'] = 'generating_report'
        print(f"[{job_id}] Tarefa de geração de relatório iniciada...")

        # Pega os dados salvos na etapa anterior
        codigo_com_conteudo = job_info['data']['codigo_com_conteudo']
        payload_dict = job_info['data']

        resposta_agente = agente_revisor.gerar_relatorio_analise(
            tipo_analise=payload_dict['analysis_type'],
            codigo_para_analise=codigo_com_conteudo,
            instrucoes_extras=payload_dict.get('instrucoes_extras')
        )
        report = resposta_agente['reposta_final']
        
        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")

    except Exception as e:
        print(f"ERRO FATAL na geração do relatório [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = f"Erro ao comunicar com a OpenAI: {e}"

def run_workflow_task(job_id: str):
    """
    Tarefa 3: Executa o fluxo de trabalho pós-aprovação do usuário.
    """
    try:
        print(f"[{job_id}] Iniciando workflow pós-aprovação...")
        job_info = jobs[job_id]
        original_analysis_type = job_info['data']['analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        previous_step_result = None
        resultado_refatoracao = None
        resultado_agrupamento = None

        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            agent_params = step['params'].copy()
            
            if i == 0:
                relatorio_aprovado = job_info['data']['analysis_report']
                instrucoes_iniciais = job_info['data'].get('instrucoes_extras')
                observacoes_aprovacao = job_info['data'].get('observacoes_aprovacao')

                instrucoes_completas = relatorio_aprovado
                if instrucoes_iniciais:
                    instrucoes_completas += f"\n\n--- INSTRUÇÕES ADICIONAIS DO USUÁRIO (INICIAL) ---\n{instrucoes_iniciais}"
                if observacoes_aprovacao:
                    instrucoes_completas += f"\n\n--- OBSERVAÇÕES DA APROVAÇÃO (APLICAR COM PRIORIDADE) ---\n{observacoes_aprovacao}"
                
                agent_params.update({'codigo': instrucoes_completas})
            else:
                agent_params['codigo'] = str(previous_step_result)
            
            agent_response = step['agent_function'](**agent_params)
            json_string = agent_response['resultado']['reposta_final'].replace("```json", '').replace("```", '')
            previous_step_result = json.loads(json_string)
            if i == 0: resultado_refatoracao = previous_step_result
            else: resultado_agrupamento = previous_step_result
        
        job_info['status'] = 'populating_data'
        dados_preenchidos = preenchimento.main(json_agrupado=resultado_agrupamento, json_inicial=resultado_refatoracao)
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(nome_repo=job_info['data']['repo_name'], dados_agrupados=dados_finais_formatados)
        job_info['status'] = 'completed'
        print(f"[{job_id}] Processo concluído com sucesso!")
    except Exception as e:
        print(f"ERRO FATAL na tarefa de workflow [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


# --- Endpoints da API ---
@app.post("/jobs/start", response_model=StartJobResponse, tags=["Jobs"])
def start_new_job(payload: StartJobPayload, background_tasks: BackgroundTasks):
    """Inicia o primeiro estágio: apenas a leitura dos arquivos."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'starting', 'data': {}, 'error': None}
    background_tasks.add_task(run_file_reading_task, job_id, payload)
    return StartJobResponse(job_id=job_id)

@app.post("/jobs/{job_id}/generate_report", tags=["Jobs"])
def generate_report(job_id: str, background_tasks: BackgroundTasks):
    """Dispara o segundo estágio: a geração do relatório pela IA."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado")
    if job['status'] != 'files_read_awaits_analysis':
        raise HTTPException(status_code=400, detail=f"O job não está no estado correto ('files_read_awaits_analysis'). Estado atual: {job['status']}")
    
    background_tasks.add_task(run_report_generation_task, job_id)
    return {"message": "Comando para gerar relatório recebido. Acompanhe o status."}

@app.get("/jobs/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """Consulta o status e os resultados de um job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado")
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        files_read=job['data'].get('files_read'),
        analysis_report=job['data'].get('analysis_report'),
        error_details=job.get('error')
    )

@app.post("/update-job-status", tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    """Aprova ou rejeita um relatório de análise para iniciar o workflow final."""
    job = jobs.get(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        job['status'] = 'workflow_started'
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}
