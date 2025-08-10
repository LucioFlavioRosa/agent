# Arquivo: mcp_server_fastapi.py (VERSÃO COMPLETA, FINAL E COM CORREÇÃO CORS)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict

# [NOVO E IMPORTANTE] Importe o CORSMiddleware para corrigir o "Failed to fetch"
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do seu projeto ---
# Certifique-se de que estes imports correspondem à sua estrutura de pastas.
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
    description="Um servidor para orquestrar agentes de IA com status assíncrono.",
    version="3.1.0"  # Versão incrementada com a correção CORS
)

# [NOVO] Bloco de configuração do CORS
# Permite que o frontend (rodando em uma porta/endereço diferente) se comunique com este backend.
origins = [
    "*",  # Permite todas as origens. Ideal para desenvolvimento.
    # Em produção, você pode restringir, por exemplo:
    # "https://seu-frontend.azurewebsites.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc)
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

# Armazenamento em memória para os jobs.
jobs: Dict[str, Dict] = {} 

# Registro de workflows pós-aprovação.
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

def run_initial_analysis_task(job_id: str, payload: StartJobPayload):
    """
    Orquestra a análise inicial usando as funções refatoradas do agente.
    """
    try:
        # ESTÁGIO 1: Pede ao agente para LER os arquivos.
        jobs[job_id]['status'] = 'reading_files'
        print(f"[{job_id}] Pedindo ao agente para ler os arquivos...")
        
        codigo_com_conteudo = agente_revisor.ler_codigo_do_repositorio(
            repositorio=payload.repo_name,
            tipo_analise=payload.analysis_type,
            nome_branch=payload.branch_name
        )
        nomes_dos_arquivos = list(codigo_com_conteudo.keys())

        # ATUALIZAÇÃO INTERMEDIÁRIA
        jobs[job_id]['status'] = 'files_read_pending_analysis'
        jobs[job_id]['data']['files_read'] = nomes_dos_arquivos
        jobs[job_id]['data']['codigo_com_conteudo'] = codigo_com_conteudo
        print(f"[{job_id}] Agente leu {len(nomes_dos_arquivos)} arquivos com sucesso.")

        # ESTÁGIO 2: Pede ao agente para GERAR o relatório.
        jobs[job_id]['status'] = 'generating_report'
        print(f"[{job_id}] Pedindo ao agente para gerar o relatório...")

        resposta_agente = agente_revisor.gerar_relatorio_analise(
            tipo_analise=payload.analysis_type,
            codigo_para_analise=codigo_com_conteudo,
            instrucoes_extras=payload.instrucoes_extras
        )
        report = resposta_agente['reposta_final']
        
        # ATUALIZAÇÃO FINAL
        jobs[job_id]['status'] = 'pending_approval'
        jobs[job_id]['data']['analysis_report'] = report
        jobs[job_id]['data'].update(payload.dict())
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação.")

    except Exception as e:
        print(f"ERRO FATAL na tarefa de análise [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


def run_workflow_task(job_id: str):
    """
    Usa o relatório já salvo no job, evitando reler o repositório.
    """
    try:
        print(f"[{job_id}] Iniciando workflow pós-aprovação...")
        job_info = jobs[job_id]
        original_analysis_type = job_info['data']['analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        previous_step_result = None
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
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'starting', 'data': {},'error': None}
    background_tasks.add_task(run_initial_analysis_task, job_id, payload)
    return StartJobResponse(job_id=job_id)

@app.get("/jobs/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
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
