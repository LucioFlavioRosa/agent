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
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.conectores.conexao_geral import ConexaoGeral
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider, get_repository_provider_explicit
from tools.blob_report_uploader import upload_report_to_blob
from tools.blob_report_reader import read_report_from_blob

# --- Classes e dependências ---
from agents.agente_revisor import AgenteRevisor
from agents.agente_processador import AgenteProcessador
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from domain.interfaces.llm_provider_interface import ILLMProvider

# --- WORKFLOW_REGISTRY ---
def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")
valid_analysis_keys = {key: key for key in WORKFLOW_REGISTRY.keys()}
ValidAnalysisTypes = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)

def _validate_and_normalize_gitlab_repo_name(repo_name: str) -> str:
    repo_name = repo_name.strip()
    
    # Prioridade 1: Project ID numérico (formato mais robusto)
    try:
        project_id = int(repo_name)
        print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
        return str(project_id)
    except ValueError:
        pass
    
    # Prioridade 2: Path completo (namespace/projeto ou grupo/subgrupo/projeto)
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
    
    # Formato inválido
    raise HTTPException(
        status_code=400,
        detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
    )

# --- Modelos de Dados Pydantic ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
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

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA.",
    version="9.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
job_store = RedisJobStore()
analysis_name_to_job_id = {}

def create_llm_provider(model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
    model_lower = (model_name or "").lower()
    
    if "claude" in model_lower:
        return AnthropicClaudeProvider(rag_retriever=rag_retriever)
    
    else:
        return OpenAILLMProvider(rag_retriever=rag_retriever)

def _try_read_report_from_blob(analysis_name: str) -> Optional[str]:
    try:
        return read_report_from_blob(analysis_name)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Erro ao ler relatório do Blob Storage: {e}")
        return None

# --- Funções de Tarefa (Tasks) ---
def handle_task_exception(job_id: str, e: Exception, step: str, job_info: Optional[Dict] = None):
    error_message = f"Erro fatal durante a etapa '{step}': {str(e)}"
    print(f"[{job_id}] {error_message}")
    traceback.print_exc() # Adiciona o traceback completo ao log para depuração
    try:
        # Usa o job_info passado para evitar uma nova leitura do Redis se já o tivermos
        current_job_info = job_info or job_store.get_job(job_id)
        if current_job_info:
            current_job_info['status'] = 'failed'
            current_job_info['error_details'] = error_message
            job_store.set_job(job_id, current_job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

def run_workflow_task(job_id: str, start_from_step: int = 0):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        rag_retriever = AzureAISearchRAGRetriever()
        changeset_filler = ChangesetFiller()
        
        repo_name = job_info['data']['repo_name']
        repository_type = job_info['data']['repository_type']
        
        print(f"[{job_id}] Usando repositório: '{repo_name}' (tipo: {repository_type})")
        print(f"[{job_id}] Usando tipo de repositório explícito: {repository_type}")
        repository_provider = get_repository_provider_explicit(repository_type)
        
        repo_reader = ReaderGeral(repository_provider=repository_provider)
        
        workflow = WORKFLOW_REGISTRY.get(job_info['data']['original_analysis_type'])
        if not workflow: raise ValueError("Workflow não encontrado.")

        # O ponto de partida é o resultado da etapa anterior à etapa de início
        previous_step_result = job_info['data'].get(f'step_{start_from_step - 1}_result', {})
        
        # O loop agora itera sobre os passos a partir do ponto de início
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            job_info['status'] = step['status_update']
            job_store.set_job(job_id, job_info)
            
            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            llm_provider = create_llm_provider(model_para_etapa, rag_retriever)
            
            agent_params = step.get('params', {}).copy()
            agent_params.update({'usar_rag': job_info.get("data", {}).get("usar_rag", False), 'model_name': model_para_etapa})
            
           
            input_para_etapa = previous_step_result
            observacoes_humanas = job_info['data'].get('instrucoes_extras_aprovacao')

            # Se esta é a primeira etapa a ser executada NESTA tarefa E a tarefa foi iniciada
            # a partir de um passo > 0 (ou seja, foi retomada após aprovação) E existem observações...
            if i == 0 and start_from_step > 0 and observacoes_humanas:
                print(f"[{job_id}] Incorporando observações humanas da aprovação ao contexto.")
                input_para_etapa = {
                    "resultado_etapa_anterior": previous_step_result,
                    "observacoes_prioritarias_do_usuario": observacoes_humanas
                }

            # Flag para controlar se o relatório foi gerado pelo agente ou lido do Blob
            report_was_generated_by_agent = True

            # Lógica de uso inteligente de relatórios do Blob Storage para etapa de índice 0
            if current_step_index == 0:
                gerar_novo_relatorio = job_info['data'].get('gerar_novo_relatorio', True)
                analysis_name = job_info['data'].get('analysis_name')
                
                if not gerar_novo_relatorio and analysis_name:
                    print(f"[{job_id}] Tentando ler relatório existente do Blob Storage: {analysis_name}")
                    existing_report = _try_read_report_from_blob(analysis_name)
                    
                    if existing_report:
                        print(f"[{job_id}] Relatório encontrado no Blob Storage, usando relatório existente")
                        agent_response = {
                            'resultado': {
                                'reposta_final': {
                                    'reposta_final': json.dumps({"relatorio": existing_report}, ensure_ascii=False)
                                }
                            }
                        }
                        report_was_generated_by_agent = False
                    else:
                        print(f"[{job_id}] Relatório não encontrado no Blob Storage, gerando novo relatório via agente")
                        agent_response = None
                else:
                    print(f"[{job_id}] Configurado para gerar novo relatório via agente")
                    agent_response = None
            else:
                agent_response = None

            # Se agent_response não foi definido pela lógica do Blob Storage, chama o agente normalmente
            if agent_response is None:
                agent_type = step.get("agent_type")
                if agent_type == "revisor":
                    agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
                    # O input para a primeira etapa do job vem do payload; para as seguintes, do contexto
                    instrucoes = job_info['data']['instrucoes_extras'] if current_step_index == 0 else json.dumps(input_para_etapa, indent=2, ensure_ascii=False)
                    agent_params.update({
                        'repositorio': job_info['data']['repo_name'], 
                        'nome_branch': job_info['data']['branch_name'], 
                        'instrucoes_extras': instrucoes,
                        'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
                        'repository_type': repository_type
                    })
                    print(f"[{job_id}] Agente Revisor: repositorio='{agent_params['repositorio']}', branch='{agent_params['nome_branch']}', tipo='{repository_type}'")
                    agent_response = agente.main(**agent_params)
                elif agent_type == "processador":
                    agente = AgenteProcessador(llm_provider=llm_provider)
                    # O input para a primeira etapa do job vem do payload; para as seguintes, do contexto
                    agent_params['codigo'] = {"instrucoes_iniciais": job_info['data']['instrucoes_extras']} if current_step_index == 0 else input_para_etapa
                    agent_params['repository_type'] = repository_type
                    agent_response = agente.main(**agent_params)
                else:
                    raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")

            json_string = agent_response['resultado']['reposta_final'].get('reposta_final', '')
            if not json_string.strip(): raise ValueError(f"IA retornou resposta vazia.")

            current_step_result = json.loads(json_string.replace("", "").replace("", "").strip())

            job_info['data'][f'step_{current_step_index}_result'] = current_step_result
            previous_step_result = current_step_result
            
            if current_step_index == 0:
                if job_info['data'].get('gerar_relatorio_apenas') is True:
                    report_text = current_step_result.get("relatorio", json.dumps(current_step_result, indent=2, ensure_ascii=False))
                    job_info['data']['analysis_report'] = report_text
                    
                    # Salva no Blob Storage apenas se o relatório foi gerado pelo agente
                    if job_info['data'].get('analysis_name') and report_text and report_was_generated_by_agent:
                        try:
                            blob_url = upload_report_to_blob(report_text, job_info['data']['analysis_name'])
                            job_info['data']['report_blob_url'] = blob_url
                            print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
                        except Exception as e:
                            print(f"[{job_id}] Erro ao salvar relatório no Blob Storage: {e}")
                    
                    print(f"[{job_id}] Modo 'gerar_relatorio_apenas' ativo. Finalizando.")
                    job_info['status'] = 'completed'
                    job_store.set_job(job_id, job_info)
                    return 
            
            if step.get('requires_approval'):
                print(f"[{job_id}] Etapa requer aprovação.")

                report_text = current_step_result.get("relatorio", json.dumps(current_step_result, indent=2, ensure_ascii=False))
                job_info['data']['analysis_report'] = report_text
                
                # Salva no Blob Storage apenas se o relatório foi gerado pelo agente
                if job_info['data'].get('analysis_name') and report_text and report_was_generated_by_agent:
                    try:
                        blob_url = upload_report_to_blob(report_text, job_info['data']['analysis_name'])
                        job_info['data']['report_blob_url'] = blob_url
                        print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
                    except Exception as e:
                        print(f"[{job_id}] Erro ao salvar relatório no Blob Storage: {e}")
                
                job_info['status'] = 'pending_approval'
                job_info['data']['paused_at_step'] = current_step_index
                job_store.set_job(job_id, job_info)
                return

        workflow_steps = workflow.get("steps", [])
        num_total_steps = len(workflow_steps)

        # 'previous_step_result' já contém o resultado da última etapa, como esperado.
        resultado_agrupamento = previous_step_result
        print(f"[{job_id}] Resultado final (última etapa) atribuído a 'resultado_agrupamento'.")

        # Inicializa a variável para o caso de haver apenas uma etapa.
        resultado_refatoracao = {}

        # A penúltima etapa só existe se houver 2 ou mais etapas no workflow.
        if num_total_steps >= 2:
            # O índice da penúltima etapa é o total de etapas menos 2 (pois a contagem começa em 0).
            penultimate_step_index = num_total_steps - 2
            resultado_refatoracao = job_info['data'].get(f'step_{penultimate_step_index}_result', {})
            print(
                f"[{job_id}] Resultado da penúltima etapa (etapa {penultimate_step_index}) atribuído a 'resultado_refatoracao'.")
        elif num_total_steps == 1:
            # Se houver apenas uma etapa, podemos considerar que o 'resultado_refatoracao'
            # (que geralmente contém o conteúdo completo dos arquivos) é o mesmo que o resultado final.
            # Isso garante que a função de preenchimento ('changeset_filler') tenha os dados necessários.
            resultado_refatoracao = previous_step_result
            print(f"[{job_id}] Workflow com apenas uma etapa. 'resultado_refatoracao' usará o resultado final.")

        # Agora, o resto do seu código funcionará de forma genérica
        job_info['data']['diagnostic_logs'] = {"penultimate_result": resultado_refatoracao,
                                               "final_result": resultado_agrupamento}

        job_info['status'] = 'populating_data'
        job_store.set_job(job_id, job_info)

        dados_preenchidos = changeset_filler.main(json_agrupado=resultado_agrupamento,
                                                  json_inicial=resultado_refatoracao)

        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})

        print(f"[{job_id}] Atualizando status para 'committing_to_github' antes de iniciar commits...")
        job_info['status'] = 'committing_to_github'
        job_store.set_job(job_id, job_info)
        
        branch_base_para_pr = job_info['data'].get('branch_name', 'main')
        
        print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")
        print(f"[{job_id}] Chamando processar_e_subir_mudancas_agrupadas...")
        
        conexao_geral = ConexaoGeral.create_with_defaults()
        repo = conexao_geral.connection(
            repositorio=repo_name,
            repository_type=repository_type,
            repository_provider=repository_provider
        )
        
        commit_results = []
        for grupo in dados_finais_formatados["grupos"]:
            resultado_branch = processar_branch_por_provedor(
                repo=repo,
                nome_branch=grupo["branch_sugerida"],
                branch_de_origem=branch_base_para_pr,
                branch_alvo_do_pr=branch_base_para_pr,
                mensagem_pr=grupo["titulo_pr"],
                descricao_pr=grupo["resumo_do_pr"],
                conjunto_de_mudancas=grupo["conjunto_de_mudancas"],
                repository_type=repository_type
            )
            commit_results.append(resultado_branch)
        
        print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
        job_info['data']['commit_details'] = commit_results

        job_info['status'] = 'completed'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")
        # --- FIM DA LÓGICA DE COMMIT ---

    except Exception as e:
        traceback.print_exc()
        handle_task_exception(job_id, e, job_info.get('status', 'workflow') if job_info else 'workflow', job_info)

# --- Endpoints da API ---
@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    # Validação e normalização específica para GitLab
    normalized_repo_name = payload.repo_name
    if payload.repository_type == 'gitlab':
        normalized_repo_name = _validate_and_normalize_gitlab_repo_name(payload.repo_name)
        print(f"GitLab - Repo original: '{payload.repo_name}', normalizado: '{normalized_repo_name}'")
    
    job_id = str(uuid.uuid4())
    analysis_type_str = payload.analysis_type.value
    initial_job_data = {
        'status': 'starting',
        'data': {
            'repo_name': normalized_repo_name,  # Usa o valor normalizado
            'original_repo_name': payload.repo_name,  # Preserva o valor original para rastreabilidade
            'branch_name': payload.branch_name,
            'original_analysis_type': analysis_type_str,
            'instrucoes_extras': payload.instrucoes_extras,
            'model_name': payload.model_name,
            'usar_rag': payload.usar_rag,
            'gerar_relatorio_apenas': payload.gerar_relatorio_apenas,
            'gerar_novo_relatorio': payload.gerar_novo_relatorio,
            'arquivos_especificos': payload.arquivos_especificos,
            'analysis_name': payload.analysis_name,
            'repository_type': payload.repository_type
        },
        'error_details': None
    }
    
    job_store.set_job(job_id, initial_job_data)
    
    if payload.analysis_name:
        analysis_name_to_job_id[payload.analysis_name] = job_id
    
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type})")
    
    # A chamada agora é sempre para a mesma função, começando do passo 0
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=job_id)
    
@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    if not job or job.get('status') != 'pending_approval':
        raise HTTPException(status_code=400, detail="Job não encontrado ou não está aguardando aprovação.")
    
    if payload.action == 'approve':
        job['data']['instrucoes_extras_aprovacao'] = payload.instrucoes_extras
        job['status'] = 'workflow_started'
        
        # Descobre de qual passo continuar
        paused_step = job['data'].get('paused_at_step', 0)
        start_from_step = paused_step + 1
        
        job_store.set_job(payload.job_id, job)
        
        # A chamada agora continua o workflow a partir do passo seguinte ao da pausa
        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)
        
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida."}
    
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

    blob_url = job.get("data", {}).get("report_blob_url")
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)

@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job associado não encontrado ou expirado")
    
    report = job.get("data", {}).get("analysis_report")
    blob_url = job.get("data", {}).get("report_blob_url")
    
    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=report,
        report_blob_url=blob_url
    )

@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    original_job = job_store.get_job(job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail="Job original não encontrado ou expirado")
    
    report = original_job.get("data", {}).get("analysis_report")
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado no job original")
    
    original_repo_name = original_job['data']['repo_name']
    original_repository_type = original_job['data']['repository_type']
    
    # Validação específica para GitLab se necessário
    normalized_repo_name = original_repo_name
    if original_repository_type == 'gitlab':
        normalized_repo_name = _validate_and_normalize_gitlab_repo_name(original_repo_name)
        print(f"GitLab derivado - Repo original: '{original_repo_name}', normalizado: '{normalized_repo_name}'")
    
    new_job_id = str(uuid.uuid4())
    
    new_job_data = {
        'status': 'starting',
        'data': {
            'repo_name': normalized_repo_name,
            'original_repo_name': original_repo_name,
            'branch_name': original_job['data']['branch_name'],
            'original_analysis_type': 'implementacao',
            'instrucoes_extras': f"Gerar código baseado no seguinte relatório:\n\n{report}",
            'model_name': original_job['data'].get('model_name'),
            'usar_rag': original_job['data'].get('usar_rag', False),
            'gerar_relatorio_apenas': False,
            'gerar_novo_relatorio': True,
            'arquivos_especificos': original_job['data'].get('arquivos_especificos'),
            'analysis_name': f"{analysis_name}-implementation",
            'repository_type': original_repository_type
        },
        'error_details': None
    }
    
    job_store.set_job(new_job_id, new_job_data)
    analysis_name_to_job_id[f"{analysis_name}-implementation"] = new_job_id
    
    print(f"[{new_job_id}] Job derivado criado - Repositório: '{normalized_repo_name}' (tipo: {original_repository_type})")
    
    background_tasks.add_task(run_workflow_task, new_job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    logs = job.get("data", {}).get("diagnostic_logs")
    blob_url = job.get("data", {}).get("report_blob_url")

    try:
        if status == 'completed':
            if job.get("data", {}).get("gerar_relatorio_apenas") is True:
                return FinalStatusResponse(
                    job_id=job_id,
                    status=status,
                    analysis_report=job.get("data", {}).get("analysis_report"),
                    report_blob_url=blob_url
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
                    report_blob_url=blob_url
                )
        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs,
                report_blob_url=blob_url
            )
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")



        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")