from typing import Any, Dict
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
        
        # --- [CORREÇÃO 2] Inicializar o Resolver se ele for None ---
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

        # Passa o resolver para o ReportHandler também
        self.report_handler = ReportHandler(blob_storage, cache_service=cache_service, group_resolver=self.group_resolver)

    def start_analysis(self, payload: Any) -> Dict[str, Any]:
        # 1. Gera o job_id
        job_id = f"job_{len(self.jobs)+1}"
        
        # 2. Extração segura dos atributos do payload (pydantic ou dict)
        # Verifica se é objeto (Pydantic) ou Dicionário para evitar erros
        if isinstance(payload, dict):
            get_attr = lambda k: payload.get(k)
        else:
            get_attr = lambda k: getattr(payload, k, None)

        projeto = get_attr('projeto')
        analysis_type = get_attr('analysis_type')
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
            # 4. Se existir, retorna o relatório existente
            job_data = {
                'status': 'completed',
                'repository_type': repository_type,
                'repo_name': repo_name,
                'branch_name': branch_name,
                'analysis_type': analysis_type,
                'arquivos_especificos': arquivos_especificos,
                'instrucoes_extras': instrucoes_extras,
                'projeto': projeto,
                'analysis_name': analysis_name,
                'gerar_relatorio_apenas': gerar_relatorio_apenas,
                'retornar_lista_arquivos': retornar_lista_arquivos,
                'usuario_executor': usuario_executor,
                'report_url': None,
                'analysis_report': report_text
            }
            self.jobs[job_id] = job_data
            self.reports[job_id] = job_data
            return {
                'job_id': job_id,
                'status': 'completed',
                'analysis_report': report_text
            }

        # 5. Não existe relatório, carrega prompt
        prompt_tipo = analysis_type if analysis_type else 'default'
        try:
            prompt_base = carregar_prompt(prompt_tipo)
        except Exception:
            prompt_base = ""

        # 6. Junta prompt com instrucoes_extras
        if instrucoes_extras:
            prompt_final = f"{prompt_base}\n\n{instrucoes_extras}"
        else:
            prompt_final = prompt_base

        # 7. Envia para LLM
        # --- [CORREÇÃO 3] O self.group_resolver agora estará preenchido ---
        llm_provider = create_provider(
            model_name=None, 
            user_email=usuario_executor, 
            group_resolver=self.group_resolver
        )
        
        # Como invoke pode não existir em ILLMProviderComplete, adaptamos para executar_prompt se necessário
        # Assumindo que invoke é um wrapper ou que você vai usar executar_prompt
        try:
             # Se a classe AmazonBedrockProvider tiver 'invoke', usa ele. Se tiver 'executar_prompt', usa ele.
            if hasattr(llm_provider, 'invoke'):
                llm_response = llm_provider.invoke(prompt_final)
            else:
                # Adaptação para usar o método que vimos no código anterior
                resp_dict = llm_provider.executar_prompt(
                    tipo_tarefa=prompt_tipo,
                    prompt_principal=prompt_final,
                    job_id=job_id
                )
                llm_response = resp_dict.get('reposta_final', '')

            report_text = llm_response if isinstance(llm_response, str) else str(llm_response)
            
        except Exception as e:
            print(f"[WORKFLOW-ERRO] Erro na chamada do LLM: {e}", flush=True)
            raise e

        # 8. Salva job e relatório
        job_data = {
            'status': 'completed',
            'repository_type': repository_type,
            'repo_name': repo_name,
            'branch_name': branch_name,
            'analysis_type': analysis_type,
            'arquivos_especificos': arquivos_especificos,
            'instrucoes_extras': instrucoes_extras,
            'projeto': projeto,
            'analysis_name': analysis_name,
            'gerar_relatorio_apenas': gerar_relatorio_apenas,
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'usuario_executor': usuario_executor,
            'report_url': None,
            'analysis_report': report_text
        }
        self.jobs[job_id] = job_data
        self.reports[job_id] = job_data
        
        return {
            'job_id': job_id,
            'status': 'completed',
            'analysis_report': report_text
        }

    def run_analysis(self, job_id: str):
        # Mantém compatibilidade
        pass

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job.get('report_url'),
            'analysis_report': job.get('analysis_report')
        }

    def get_report(self, job_id: str) -> Dict[str, Any]:
        job = self.reports.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job.get('report_url'),
            'analysis_report': job.get('analysis_report')
        }
