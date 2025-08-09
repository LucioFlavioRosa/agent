# Arquivo: mcp_server_fastapi.py (VERSÃO ATUALIZADA)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal

# Seus imports de agentes e a definição do WORKFLOW_REGISTRY permanecem os mesmos.
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Definição dos Modelos de Dados com Pydantic ---

class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["design", "relatorio_teste_unitario"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None

# [ALTERADO] O payload de atualização agora aceita observações opcionais.
class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    # [NOVO] Campo opcional para adicionar ressalvas/observações durante a aprovação.
    observacoes: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error_details: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    job_id: str
    report: str

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Um servidor para orquestrar agentes de IA para análise e refatoração de código.",
    version="1.1.0" # Versão incrementada para refletir a nova funcionalidade
)

jobs = {} # O armazenamento em memória continua igual para este exemplo.

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

def run_workflow_task(job_id: str):
    try:
        print(f"[{job_id}] Iniciando workflow...")
        job_info = jobs[job_id]
        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        resultado_refatoracao, resultado_agrupamento = None, None
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            agent_params = step['params'].copy()
            
            if i == 0:
                # [ALTERADO] A lógica de construção das instruções agora inclui as observações da aprovação.
                relatorio_gerado = job_info['data']['analysis_report']
                instrucoes_iniciais = job_info['data'].get('instrucoes_extras')
                observacoes_aprovacao = job_info['data'].get('observacoes_aprovacao') # Pode ser None

                instrucoes_completas = relatorio_gerado
                if instrucoes_iniciais:
                    instrucoes_completas += f"\n\n--- INSTRUÇÕES ADICIONAIS DO USUÁRIO (INICIAL) ---\n{instrucoes_iniciais}"
                
                # [NOVO] Adiciona as novas observações da aprovação ao prompt final.
                if observacoes_aprovacao:
                    instrucoes_completas += f"\n\n--- OBSERVAÇÕES DA APROVAÇÃO (APLICAR COM PRIORIDADE) ---\n{observacoes_aprovacao}"
                
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': instrucoes_completas # Passa as instruções combinadas
                })
            else:
                agent_params['codigo'] = str(previous_step_result)
            
            agent_response = step['agent_function'](**agent_params)
            json_string = agent_response['resultado']['reposta_final'].replace("```json", '').replace("```", '')
            previous_step_result = json.loads(json_string)
            if i == 0: resultado_refatoracao = previous_step_result
            else: resultado_agrupamento = previous_step_result
        
        job_info['status'] = 'populating_data'
        print(f"[{job_id}] ... Etapa de preenchimento...")
        dados_preenchidos = preenchimento.main(json_agrupado=resultado_agrupamento, json_inicial=resultado_refatoracao)
        
        print(f"[{job_id}] ... Etapa de transformação...")
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        print(f"[{job_id}] ... Etapa de commit para o GitHub...")
        commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(nome_repo=job_info['data']['repo_name'], dados_agrupados=dados_finais_formatados)
        job_info['status'] = 'completed'
        print(f"[{job_id}] Processo concluído com sucesso!")
    except Exception as e:
        print(f"ERRO FATAL na tarefa [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

# --- Endpoints da API com FastAPI ---

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload):
    """
    Inicia um novo job de análise de código e retorna um relatório para aprovação.
    """
    try:
        resposta = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras
        )
        report = resposta['resultado']['reposta_final']
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'pending_approval',
            'data': {
                'repo_name': payload.repo_name,
                'branch_name': payload.branch_name,
                'original_analysis_type': payload.analysis_type,
                'analysis_report': report,
                'instrucoes_extras': payload.instrucoes_extras,
                # [NOVO] Prepara o campo para receber as futuras observações.
                'observacoes_aprovacao': None 
            }
        }
        return StartAnalysisResponse(job_id=job_id, report=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar o relatório de análise: {e}")

@app.post("/update-job-status", tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = jobs.get(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        # [ALTERADO] Armazena as observações do payload no dicionário do job antes de iniciar a tarefa.
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
            print(f"Aprovação do Job [{payload.job_id}] recebida com observações.")
        
        job['status'] = 'workflow_started'
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}

@app.get("/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = jobs.get(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado")
    return JobStatusResponse(job_id=job_id, status=job['status'], error_details=job.get('error'))