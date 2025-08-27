import json
import uuid
import yaml
import time
import traceback
import enum
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do projeto ---
from tools.job_store import RedisJobStore
from tools import commit_multiplas_branchs

# --- Classes e dependências ---
from agents.agente_revisor import AgenteRevisor
from agents.agente_processador import AgenteProcessador
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from tools.github_reader import GitHubRepositoryReader
from tools.github_repository_provider import GitHubRepositoryProvider
from domain.interfaces.llm_provider_interface import ILLMProvider
from domain.interfaces.repository_provider_interface import IRepositoryProvider

# --- WORKFLOW_REGISTRY ---
def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")
valid_analysis_keys = {key: key for key in WORKFLOW_REGISTRY.keys()}
ValidAnalysisTypes = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)

# --- Modelos de Dados Pydantic ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: ValidAnalysisTypes
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar esta análise.")

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
    summary: Optional[List[PullRequestSummary]] = Field(None)
    error_details: Optional[str] = Field(None)
    analysis_report: Optional[str] = Field(None)
    diagnostic_logs: Optional[Dict[str, Any]] = Field(None)
    analysis_name: Optional[str] = Field(None, description="Nome personalizado da análise, se fornecido.")

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]
    analysis_name: Optional[str] = Field(None, description="Nome personalizado da análise, se fornecido.")

class AnalysisByNameResponse(BaseModel):
    job_id: str
    analysis_name: str
    analysis_report: Optional[str]
    status: str

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA com suporte extensível a múltiplos provedores de repositório.",
    version="10.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
job_store = RedisJobStore()

# --- Mapeamento de análises por nome ---
# Este dicionário mapeia nomes de análise para job_ids para permitir busca por nome
analysis_name_to_job_id = {}

def get_repository_provider() -> IRepositoryProvider:
    """
    Factory function para obter o provedor de repositório configurado.
    
    Esta função centraliza a lógica de seleção do provedor de repositório,
    permitindo fácil extensão para múltiplos provedores no futuro.
    Por enquanto, retorna sempre GitHubRepositoryProvider, mas pode ser
    estendida para ler configuração de ambiente ou payload da requisição.
    
    Returns:
        IRepositoryProvider: Instância do provedor de repositório configurado
    
    Note:
        Futuras implementações podem incluir:
        - Leitura de variável de ambiente REPOSITORY_PROVIDER
        - Seleção baseada no formato do repo_name
        - Configuração via payload da requisição
    
    Example:
        # Implementação futura:
        # provider_type = os.getenv("REPOSITORY_PROVIDER", "github").lower()
        # if provider_type == "gitlab":
        #     return GitLabRepositoryProvider()
        # elif provider_type == "bitbucket":
        #     return BitbucketRepositoryProvider()
        # else:
        #     return GitHubRepositoryProvider()
    """
    return GitHubRepositoryProvider()

def create_llm_provider(model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
    """
    Analisa o nome do modelo e instancia a classe de provedor de LLM correta.
    Esta função é o ponto central para adicionar ou alterar provedores.
    """
    model_lower = (model_name or "").lower()
    
    if "claude" in model_lower:
        return AnthropicClaudeProvider(rag_retriever=rag_retriever)
    
    else:
        return OpenAILLMProvider(rag_retriever=rag_retriever)


# --- Funções de Tarefa (Tasks) ---
def handle_task_exception(job_id: str, e: Exception, step: str):
    error_message = f"Erro fatal durante a etapa '{step}': {str(e)}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = job_store.get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error_details'] = error_message
            job_store.set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    """
    Executa APENAS O PRIMEIRO PASSO de um workflow para gerar um relatório
    e então para, aguardando a aprovação humana.
    """
    ob_info = None
    json_string_from_llm = ""
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        analysis_type_str = payload.analysis_type.value
        workflow = WORKFLOW_REGISTRY.get(analysis_type_str)
        first_step = workflow['steps'][0]
        
        job_info['status'] = first_step.get('status_update', 'gerando_relatorio')
        job_store.set_job(job_id, job_info)

        rag_retriever = AzureAISearchRAGRetriever()
        model_para_etapa = first_step.get('model_name', payload.model_name)
        llm_provider = create_llm_provider(model_para_etapa, rag_retriever)
        
        # Obtém o provedor de repositório configurado
        repository_provider = get_repository_provider()
        
        agent_type = first_step.get("agent_type")
        params_base = first_step.get('params', {}).copy()

        # --- LÓGICA DE CHAMADA FINAL E CORRIGIDA ---
        if agent_type == "revisor":
            repo_reader = GitHubRepositoryReader(repository_provider=repository_provider)
            agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
            
            # Chama o AgenteRevisor com os parâmetros que ele espera
            agent_response = agente.main(
                tipo_analise=params_base.get("tipo_analise"),
                repositorio=payload.repo_name,
                nome_branch=payload.branch_name,
                instrucoes_extras=payload.instrucoes_extras,
                usar_rag=payload.usar_rag,
                model_name=model_para_etapa
            )
            
        elif agent_type == "processador":
            agente = AgenteProcessador(llm_provider=llm_provider)
            
            # O input principal para o processador é a especificação técnica
            input_estruturado = {"instrucoes_iniciais": payload.instrucoes_extras}
            
            # Chama o AgenteProcessador com os parâmetros que ele espera
            agent_response = agente.main(
                tipo_analise=params_base.get("tipo_analise"),
                codigo=input_estruturado,
                instrucoes_extras=payload.instrucoes_extras, # Pode ser útil como contexto adicional
                usar_rag=payload.usar_rag,
                model_name=model_para_etapa
            )
        else:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}' no workflow.")

        provider_response = agent_response.get("resultado", {}).get("reposta_final", {})
        json_string_from_llm = provider_response.get("reposta_final", "")

        if not json_string_from_llm.strip():
            raise ValueError("A resposta da IA veio vazia.")
        
        # 1. Analisa o JSON que a IA retornou.
        parsed_response = json.loads(json_string_from_llm.replace("", "").replace("", "").strip())
        
        # 2. Pega o valor da ÚNICA chave que esperamos: "relatorio".
        #    Se a chave não existir, usa a resposta bruta como um fallback seguro.
        report_text = parsed_response.get("relatorio", json_string_from_llm)
        
        # 3. Salva o texto do relatório para a visualização do humano e para a próxima etapa.
        job_info['data']['analysis_report'] = report_text
        
        # 4. Salva o objeto JSON original para os logs de diagnóstico.
        job_info['data']['step_0_result'] = parsed_response
        
        # --- FIM DA MUDANÇA ---
        
        if payload.gerar_relatorio_apenas:
            job_info['status'] = 'completed'
        else:
            job_info['status'] = 'pending_approval'

        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Tarefa de geração de relatório concluída. Status: {job_info['status']}")

    except Exception as e:
        if job_info:
            if 'data' not in job_info: job_info['data'] = {}
            job_info['data']['diagnostic_logs'] = {
                "raw_llm_response_report_generation": json_string_from_llm
            }
            job_store.set_job(job_id, job_info)
        traceback.print_exc()
        handle_task_exception(job_id, e, job_info.get('status', 'report_generation') if job_info else 'report_generation')

def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        # Constrói as dependências genéricas
        rag_retriever = AzureAISearchRAGRetriever()
        changeset_filler = ChangesetFiller()
        
        # Obtém o provedor de repositório configurado
        repository_provider = get_repository_provider()
        repo_reader = GitHubRepositoryReader(repository_provider=repository_provider)

        workflow = WORKFLOW_REGISTRY.get(job_info['data']['original_analysis_type'])
        if not workflow: raise ValueError("Workflow não encontrado.")

        # --- FLUXO DE DADOS CORRIGIDO E FINAL ---

        # 1. O ponto de partida é o resultado estruturado da tarefa de geração de relatório.
        previous_step_result = job_info['data'].get('step_0_result', {})

        # Variáveis para armazenar os resultados importantes
        resultado_refatoracao_etapa = {}
        resultado_agrupamento_etapa = {}

        # 2. O loop executa os passos restantes do workflow (do segundo em diante).
        etapas_do_workflow = workflow.get('steps', [])[1:]
        
        for i, step in enumerate(etapas_do_workflow):
            job_info['status'] = step['status_update']
            job_store.set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo do workflow: {job_info['status']}")

            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            llm_provider = create_llm_provider(model_para_etapa, rag_retriever)
            
            agent_params = step.get('params', {}).copy()
            agent_params['usar_rag'] = job_info.get("data", {}).get("usar_rag", False)
            agent_params['model_name'] = model_para_etapa
            
            agent_type = step.get("agent_type", "processador")
            
            if agent_type == "revisor":
                agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
                # O input é o relatório/plano da tarefa anterior
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': job_info['data']['analysis_report']
                })
                agent_response = agente.main(**agent_params)
            else: # processador
                agente = AgenteProcessador(llm_provider=llm_provider)
                # O input é o JSON estruturado da etapa anterior
                agent_params['codigo'] = previous_step_result
                agent_response = agente.main(**agent_params)

            json_string = agent_response['resultado']['reposta_final'].get('reposta_final', '')
            if not json_string.strip(): raise ValueError(f"IA retornou resposta vazia na etapa '{job_info['status']}'.")
            
            current_step_result = json.loads(json_string.replace("", "").replace("", "").strip())
            
            # 3. Armazena os resultados corretamente
            if i == 0:
                # O resultado da primeira etapa deste workflow é sempre a refatoração.
                resultado_refatoracao_etapa = current_step_result
            
            # O resultado da última etapa é sempre o agrupamento.
            if i == len(etapas_do_workflow) - 1:
                 resultado_agrupamento_etapa = current_step_result

            previous_step_result = current_step_result

        # 4. Processamento final usa as variáveis corretas
        job_info['data']['resultado_refatoracao'] = resultado_refatoracao_etapa
        job_info['data']['resultado_agrupamento'] = resultado_agrupamento_etapa
        job_info['data']['diagnostic_logs'] = {
            "1_json_refatoracao_inicial": resultado_refatoracao_etapa,
            "2_json_agrupamento_recebido": resultado_agrupamento_etapa
        }
        job_info['status'] = 'populating_data'
        job_store.set_job(job_id, job_info)
        
        dados_preenchidos = changeset_filler.main(
            json_agrupado=resultado_agrupamento_etapa,
            json_inicial=resultado_refatoracao_etapa
        )
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})

        job_info['status'] = 'committing_to_github'
        job_store.set_job(job_id, job_info)
        branch_base_para_pr = job_info['data'].get('branch_name', 'main')
        
        # Passa o provedor de repositório para o commit
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
            nome_repo=job_info['data']['repo_name'], 
            dados_agrupados=dados_finais_formatados,
            base_branch=branch_base_para_pr,
            repository_provider=repository_provider
        )
        job_info['data']['commit_details'] = commit_results

        job_info['status'] = 'completed'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")

    except Exception as e:
        traceback.print_exc()
        handle_task_exception(job_id, e, job_info.get('status', 'workflow') if job_info else 'workflow')

# --- Endpoints da API ---
@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    analysis_type_str = payload.analysis_type.value
    initial_job_data = {
        'status': 'starting',
        'data': {
            'repo_name': payload.repo_name,
            'branch_name': payload.branch_name,
            'original_analysis_type': analysis_type_str,
            'instrucoes_extras': payload.instrucoes_extras,
            'model_name': payload.model_name, # Salva o modelo escolhido para uso futuro
            'analysis_name': payload.analysis_name  # Salva o nome personalizado
        },
        'error_details': None
    }
    
    job_store.set_job(job_id, initial_job_data)
    
    # Se um nome de análise foi fornecido, mapeia para o job_id
    if payload.analysis_name:
        analysis_name_to_job_id[payload.analysis_name] = job_id
        print(f"Análise '{payload.analysis_name}' mapeada para job_id: {job_id}")
    
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    if job['status'] not in ['pending_approval']:
        if job['status'] == 'completed':
            return {"job_id": payload.job_id, "status": "completed", "message": "Este job já foi concluído."}
        raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        
        job['status'] = 'workflow_started'
        job_store.set_job(payload.job_id, job)
        
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida. Processo iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    report = job.get("data", {}).get("analysis_report")
    if not report:
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get('status')}")

    analysis_name = job.get("data", {}).get("analysis_name")
    return ReportResponse(job_id=job_id, analysis_report=report, analysis_name=analysis_name)

@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    """
    Busca uma análise pelo nome personalizado fornecido durante a criação.
    
    Este endpoint permite que usuários recuperem análises usando nomes
    amigáveis em vez de job_ids, facilitando a organização e recuperação
    de análises específicas.
    """
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    job = job_store.get_job(job_id)
    if not job:
        # Remove mapeamento inválido
        analysis_name_to_job_id.pop(analysis_name, None)
        raise HTTPException(status_code=404, detail=f"Job associado à análise '{analysis_name}' não encontrado ou expirado")
    
    analysis_report = job.get("data", {}).get("analysis_report")
    status = job.get("status", "unknown")
    
    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=analysis_report,
        status=status
    )

@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    """
    Inicia geração de código baseada em um relatório de análise existente.
    
    Este endpoint permite que usuários aprovem um relatório de análise
    e iniciem automaticamente a geração de código correspondente,
    implementando um workflow de duas etapas: análise → aprovação → implementação.
    """
    # Busca o job original pelo nome da análise
    original_job_id = analysis_name_to_job_id.get(analysis_name)
    if not original_job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    original_job = job_store.get_job(original_job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail=f"Job original da análise '{analysis_name}' não encontrado ou expirado")
    
    # Verifica se o job original tem um relatório disponível
    analysis_report = original_job.get("data", {}).get("analysis_report")
    if not analysis_report:
        raise HTTPException(status_code=400, detail=f"Relatório não disponível para a análise '{analysis_name}'")
    
    # Cria novo job para geração de código
    new_job_id = str(uuid.uuid4())
    original_data = original_job.get("data", {})
    
    new_job_data = {
        'status': 'workflow_started',
        'data': {
            'repo_name': original_data.get('repo_name'),
            'branch_name': original_data.get('branch_name'),
            'original_analysis_type': original_data.get('original_analysis_type'),
            'instrucoes_extras': original_data.get('instrucoes_extras'),
            'model_name': original_data.get('model_name'),
            'analysis_name': f"{analysis_name}-codegen",
            'analysis_report': analysis_report,
            'step_0_result': original_job.get('data', {}).get('step_0_result', {}),
            'usar_rag': original_data.get('usar_rag', False)
        },
        'error_details': None
    }
    
    job_store.set_job(new_job_id, new_job_data)
    
    # Mapeia o novo nome para o novo job_id
    codegen_analysis_name = f"{analysis_name}-codegen"
    analysis_name_to_job_id[codegen_analysis_name] = new_job_id
    
    # Inicia o workflow de geração de código
    background_tasks.add_task(run_workflow_task, new_job_id)
    
    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    logs = job.get("data", {}).get("diagnostic_logs")
    analysis_name = job.get("data", {}).get("analysis_name")

    try:
        if status == 'completed':
            if job.get("data", {}).get("gerar_relatorio_apenas") is True:
                return FinalStatusResponse(
                    job_id=job_id,
                    status=status,
                    analysis_report=job.get("data", {}).get("analysis_report"),
                    analysis_name=analysis_name
                )
            else:
                summary_list = []
                commit_details = job.get("data", {}).get("commit_details", [])
                for pr_info in commit_details:
                    if pr_info.get("success") and pr_info.get("pr_url"):
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=pr_info.get("pr_url"),
                                branch_name=pr_info.get("branch_name"),
                                arquivos_modificados=pr_info.get("arquivos_modificados", [])
                            )
                        )
                return FinalStatusResponse(
                    job_id=job_id, 
                    status=status, 
                    summary=summary_list,
                    diagnostic_logs=logs,
                    analysis_name=analysis_name
                )
        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs,
                analysis_name=analysis_name
            )
        else:
            return FinalStatusResponse(
                job_id=job_id, 
                status=status, 
                analysis_name=analysis_name
            )
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")