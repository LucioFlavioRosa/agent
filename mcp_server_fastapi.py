# Arquivo: mcp_server_fastapi.py (VERSÃO COMPLETA E ATUALIZADA)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict

# --- Módulos do seu projeto ---
# Certifique-se de que estes imports correspondem à sua estrutura de pastas.
# [IMPORTANTE] Assumimos que a lógica de leitura de arquivos está em 'tools/leitor_de_arquivos.py'
from agents import agente_revisor
from tools import leitor_de_arquivos, preenchimento, commit_multiplas_branchs

# --- Definição dos Modelos de Dados (Pydantic) ---

# [NOVO] Payload para iniciar um job.
class StartJobPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["design", "relatorio_teste_unitario"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None

# [NOVO] Resposta imediata ao iniciar um job.
class StartJobResponse(BaseModel):
    job_id: str

# [ALTERADO] Modelo de resposta de status, agora mais completo.
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    files_read: Optional[List[str]] = None
    analysis_report: Optional[str] = None
    error_details: Optional[str] = None

# [ORIGINAL] Payload para aprovar/rejeitar, permanece o mesmo.
class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None


# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Um servidor para orquestrar agentes de IA para análise e refatoração de código com status assíncrono.",
    version="2.0.0" 
)

# Armazenamento em memória para os jobs. Em produção, considere usar um banco de dados como Redis.
jobs: Dict[str, Dict] = {} 

# [ORIGINAL] Registro de workflows pós-aprovação. Não precisa de alterações.
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

# [NOVO] Tarefa 1: Realiza a análise inicial (leitura de arquivos + relatório da IA)
def run_initial_analysis_task(job_id: str, payload: StartJobPayload):
    """
    Executa a análise em estágios, atualizando o status do job para o frontend consultar.
    """
    try:
        # ESTÁGIO 1: Lendo os arquivos do repositório
        jobs[job_id]['status'] = 'reading_files'
        print(f"[{job_id}] Estágio 1: Lendo arquivos do repo '{payload.repo_name}'...")
        
        arquivos_com_conteudo = leitor_de_arquivos.main(
            nome_repo=payload.repo_name,
            tipo_de_analise=payload.analysis_type,
            nome_branch=payload.branch_name
        )
        nomes_dos_arquivos = list(arquivos_com_conteudo.keys())

        # ATUALIZAÇÃO INTERMEDIÁRIA: Disponibiliza a lista de arquivos lidos
        jobs[job_id]['status'] = 'files_read_pending_analysis'
        jobs[job_id]['data']['files_read'] = nomes_dos_arquivos
        print(f"[{job_id}] {len(nomes_dos_arquivos)} arquivos lidos com sucesso.")

        # ESTÁGIO 2: Gerando o relatório com a IA (a parte mais demorada)
        jobs[job_id]['status'] = 'generating_report'
        print(f"[{job_id}] Estágio 2: Gerando relatório de análise...")

        # [IMPORTANTE] Assumindo que seu agente pode ser chamado com o conteúdo já lido.
        # Se necessário, ajuste seu `agente_revisor` para ter uma função que aceite `arquivos_com_conteudo`.
        resposta_agente = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras
            # O ideal seria passar o `arquivos_com_conteudo` para não ler o repo duas vezes.
        )
        report = resposta_agente['resultado']['reposta_final']
        
        # ATUALIZAÇÃO FINAL: Disponibiliza o relatório e aguarda aprovação humana.
        jobs[job_id]['status'] = 'pending_approval' # Status final para esta tarefa.
        jobs[job_id]['data']['analysis_report'] = report
        # Os dados do payload original também são importantes para a próxima fase.
        jobs[job_id]['data'].update(payload.dict())
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")

    except Exception as e:
        print(f"ERRO FATAL na tarefa de análise [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

# [ORIGINAL] Tarefa 2: Roda o workflow após a aprovação do usuário. Não precisa de alterações.
def run_workflow_task(job_id: str):
    """
    Processa a refatoração/criação de código e commita no GitHub.
    Esta função é chamada APÓS o usuário aprovar o job via /update-job-status.
    """
    try:
        print(f"[{job_id}] Iniciando workflow pós-aprovação...")
        job_info = jobs[job_id]
        original_analysis_type = job_info['data']['analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        resultado_refatoracao, resultado_agrupamento = None, None
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            agent_params = step['params'].copy()
            
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
        print(f"ERRO FATAL na tarefa de workflow [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

# --- Endpoints da API ---

@app.post("/jobs/start", response_model=StartJobResponse, tags=["Jobs"])
def start_new_job(payload: StartJobPayload, background_tasks: BackgroundTasks):
    """
    Inicia um novo job de análise. Responde imediatamente com um job_id.
    O progresso deve ser consultado no endpoint /jobs/status/{job_id}.
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'starting',
        'data': {},
        'error': None
    }
    
    background_tasks.add_task(run_initial_analysis_task, job_id, payload)
    
    return StartJobResponse(job_id=job_id)

@app.get("/jobs/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Consulta o status e os resultados intermediários/finais de um job.
    """
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
    """
    Aprova ou rejeita um job que está no estado 'pending_approval'.
    """
    job = jobs.get(payload.job_id)
    if not job: 
        raise HTTPException(status_code=404, detail="Job ID não encontrado")
    if job['status'] != 'pending_approval': 
        raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
            print(f"Aprovação do Job [{payload.job_id}] recebida com observações.")
        
        job['status'] = 'workflow_started'
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        # Limpando dados para economizar memória, opcional.
        jobs.pop(payload.job_id, None) 
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}
