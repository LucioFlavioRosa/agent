import yaml
import os
from typing import Any, Dict, Optional
from services.report_handler import ReportHandler
from tools.prompt_utils import carregar_prompt
from services.factories.llm_provider_factory import create_provider
from services.mongodb_group_resolver_service import MongoDBGroupResolverService

class SimplifiedWorkflowService:
    def __init__(self, blob_storage=None, cache_service=None, group_resolver=None):
        self.jobs = {}
        self.reports = {}
        self.blob_storage = blob_storage
        self.cache_service = cache_service
        self.workflows_config = self._load_workflows_config()  # Carrega o YAML ao iniciar
        
        # --- Inicializar o Resolver se ele for None ---
        if group_resolver is None:
            print("--- [WORKFLOW] Inicializando MongoDB Resolver internamente... ---", flush=True)
            try:
                self.group_resolver = MongoDBGroupResolverService()
                print("[WORKFLOW] MongoDB Resolver iniciado com sucesso.", flush=True)
            except Exception as e:
                print(f"[WORKFLOW-CRÍTICO] Falha ao iniciar MongoDB Resolver: {e}", flush=True)
                self.group_resolver = None
        else:
            self.group_resolver = group_resolver

        self.report_handler = ReportHandler(blob_storage, cache_service=cache_service, group_resolver=self.group_resolver)

    def _load_workflows_config(self) -> Dict:
        """Carrega o arquivo workflows.yaml da raiz ou pasta de configuração."""
        # Ajuste o caminho conforme a estrutura do seu projeto. 
        # Aqui assumo que está na raiz ou numa pasta 'config'/'tools'
        possible_paths = ["workflows.yaml", "config/workflows.yaml", "tools/workflows.yaml"]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        print(f"[WORKFLOW] Carregando configuração de: {path}", flush=True)
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"[WORKFLOW-ERRO] Erro ao ler {path}: {e}", flush=True)
        
        print("[WORKFLOW-AVISO] Arquivo workflows.yaml não encontrado!", flush=True)
        return {}

    def start_analysis(self, payload: Any) -> Dict[str, Any]:
        # 1. Gera o job_id
        job_id = f"job_{len(self.jobs)+1}"
        
        # 2. Extração segura dos atributos
        if isinstance(payload, dict):
            get_attr = lambda k: payload.get(k)
        else:
            get_attr = lambda k: getattr(payload, k, None)

        projeto = get_attr('projeto')
        analysis_type = get_attr('analysis_type') # Ex: 'analise_performance_eficiencia'
        repository_type = get_attr('repository_type')
        repo_name = get_attr('repo_name')
        branch_name = get_attr('branch_name')
        analysis_name = get_attr('analysis_name')
        usuario_executor = get_attr('usuario_executor')
        arquivos_especificos = get_attr('arquivos_especificos')
        instrucoes_extras = get_attr('instrucoes_extras')
        gerar_relatorio_apenas = get_attr('gerar_relatorio_apenas')
        retornar_lista_arquivos = get_attr('retornar_lista_arquivos')

        # 3. Verifica relatório existente
        report_text = self.report_handler.check_existing_report(
            projeto=projeto,
            analysis_type=analysis_type,
            repository_type=repository_type,
            repo_name=repo_name,
            branch_name=branch_name,
            analysis_name=analysis_name,
            user_email=usuario_executor
        )
        
        if report_text:
            return self._create_job_response(job_id, "completed", report_text, locals())

        # 4. [LÓGICA NOVA] Busca dinâmica no workflows.yaml
        # Pega a configuração para a chave analysis_type (ex: analise_performance_eficiencia)
        workflow_config = self.workflows_config.get(analysis_type)
        
        prompt_arquivo_nome = "default"
        model_name_yaml = None
        
        if workflow_config:
            steps = workflow_config.get('steps', [])
            if steps and len(steps) > 0:
                # Pega o PRIMEIRO step (índice 0) para gerar o relatório inicial
                first_step = steps[0]
                params = first_step.get('params', {})
                
                # Extrai 'tipo_analise' dos params -> Isso vira o nome do prompt
                prompt_arquivo_nome = params.get('tipo_analise', analysis_type)
                
                # Extrai o modelo específico do YAML, se houver
                model_name_yaml = first_step.get('model_name')
                
                print(f"[DEBUG] YAML Config encontrado. Step 1 Prompt: '{prompt_arquivo_nome}', Model: '{model_name_yaml}'", flush=True)
            else:
                print(f"[AVISO] Chave '{analysis_type}' encontrada no YAML mas sem 'steps'. Usando default.", flush=True)
                prompt_arquivo_nome = analysis_type
        else:
            print(f"[AVISO] Workflow '{analysis_type}' não encontrado no YAML. Tentando usar o nome direto.", flush=True)
            prompt_arquivo_nome = analysis_type

        # 5. Carrega o prompt com o nome descoberto dinamicamente
        try:
            prompt_base = carregar_prompt(prompt_arquivo_nome)
        except Exception as e:
            print(f"[AVISO] Prompt '{prompt_arquivo_nome}' não encontrado: {e}", flush=True)
            prompt_base = ""

        # 6. Junta prompt com instrucoes_extras
        prompt_final = f"{prompt_base}\n\n{instrucoes_extras}" if instrucoes_extras else prompt_base

        # 7. Envia para LLM
        # Passamos o model_name_yaml se ele foi definido no arquivo de configuração
        llm_provider = create_provider(
            model_name=model_name_yaml, 
            user_email=usuario_executor, 
            group_resolver=self.group_resolver
        )
        
        try:
            if hasattr(llm_provider, 'invoke'):
                llm_response = llm_provider.invoke(prompt_final)
            else:
                # Passamos o tipo_tarefa correto para o provedor saber qual system prompt usar (se aplicável)
                resp_dict = llm_provider.executar_prompt(
                    tipo_tarefa=prompt_arquivo_nome,
                    prompt_principal=prompt_final,
                    model_name=model_name_yaml, # Passa o modelo específico (ex: o us.anthropic...)
                    job_id=job_id
                )
                llm_response = resp_dict.get('reposta_final', '')

            report_text = llm_response if isinstance(llm_response, str) else str(llm_response)
            
        except Exception as e:
            print(f"[WORKFLOW-ERRO] Erro na chamada do LLM: {e}", flush=True)
            raise e

        # 8. Salva e retorna
        return self._create_job_response(job_id, "completed", report_text, locals())

    def _create_job_response(self, job_id, status, report_text, local_vars):
        """Helper para criar a resposta padronizada e salvar no estado."""
        # Extrai variáveis do escopo local passado
        job_data = {
            'status': status,
            'repository_type': local_vars.get('repository_type'),
            'repo_name': local_vars.get('repo_name'),
            'branch_name': local_vars.get('branch_name'),
            'analysis_type': local_vars.get('analysis_type'),
            'arquivos_especificos': local_vars.get('arquivos_especificos'),
            'instrucoes_extras': local_vars.get('instrucoes_extras'),
            'projeto': local_vars.get('projeto'),
            'analysis_name': local_vars.get('analysis_name'),
            'usuario_executor': local_vars.get('usuario_executor'),
            'report_url': None,
            'analysis_report': report_text
        }
        self.jobs[job_id] = job_data
        self.reports[job_id] = job_data
        
        return {
            'job_id': job_id,
            'status': status,
            'analysis_report': report_text
        }

    # ... métodos get_status, get_report e run_analysis mantidos iguais ...
    def run_analysis(self, job_id: str): pass

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job: return None
        return {'job_id': job_id, 'status': job['status'], 'report_url': job.get('report_url'), 'analysis_report': job.get('analysis_report')}

    def get_report(self, job_id: str) -> Dict[str, Any]:
        job = self.reports.get(job_id)
        if not job: return None
        return {'job_id': job_id, 'status': job['status'], 'report_url': job.get('report_url'), 'analysis_report': job.get('analysis_report')}
