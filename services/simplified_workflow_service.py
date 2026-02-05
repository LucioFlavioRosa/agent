import yaml
import os
import uuid
from typing import Any, Dict, Optional
from services.report_handler import ReportHandler
from tools.prompt_utils import carregar_prompt
from services.factories.llm_provider_factory import create_provider
from services.mongodb_group_resolver_service import MongoDBGroupResolverService

class SimplifiedWorkflowService:
    def __init__(self, blob_storage=None, cache_service=None, group_resolver=None):
        # Armazenamento em memória (Simulando banco de dados para este exemplo)
        self.jobs = {} 
        self.blob_storage = blob_storage
        self.cache_service = cache_service
        self.workflows_config = self._load_workflows_config()
        
        # --- Inicializar o Resolver ---
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
        """Carrega o arquivo workflows.yaml."""
        possible_paths = ["workflows.yaml", "config/workflows.yaml", "tools/workflows.yaml"]
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        print(f"[WORKFLOW] Carregando configuração de: {path}", flush=True)
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"[WORKFLOW-ERRO] Erro ao ler {path}: {e}", flush=True)
        return {}

    def start_analysis(self, payload: Any) -> Dict[str, Any]:
        """
        PASSO 1: Gera o relatório, salva no Blob e pausa para aprovação.
        """
        # 1. Gera Job ID robusto (UUID)
        job_id = str(uuid.uuid4())
        
        # 2. Extração de atributos
        if isinstance(payload, dict):
            get_attr = lambda k: payload.get(k)
        else:
            get_attr = lambda k: getattr(payload, k, None)

        # Monta o objeto job_data inicial
        job_data = {
            'job_id': job_id,
            'status': 'running',
            'projeto': get_attr('projeto'),
            'analysis_type': get_attr('analysis_type'),
            'repository_type': get_attr('repository_type'),
            'repo_name': get_attr('repo_name'),
            'branch_name': get_attr('branch_name'),
            'analysis_name': get_attr('analysis_name'),
            'usuario_executor': get_attr('usuario_executor'),
            'instrucoes_extras': get_attr('instrucoes_extras'),
            'arquivos_especificos': get_attr('arquivos_especificos'),
            # Campos de controle
            'analysis_report': None,
            'report_blob_url': None,
            'current_step': 0
        }
        self.jobs[job_id] = job_data

        # 3. Identifica configuração do YAML (Step 0 - Geração)
        workflow_config = self.workflows_config.get(job_data['analysis_type'])
        if not workflow_config:
            raise ValueError(f"Workflow '{job_data['analysis_type']}' não encontrado no YAML.")

        steps = workflow_config.get('steps', [])
        if not steps:
            raise ValueError(f"Workflow '{job_data['analysis_type']}' não possui steps configurados.")

        # Pega o Step 0 (Gerar Relatório)
        step_0 = steps[0]
        params = step_0.get('params', {})
        prompt_arquivo_nome = params.get('tipo_analise', job_data['analysis_type'])
        model_name_yaml = step_0.get('model_name')

        print(f"[{job_id}] Iniciando Step 0: {step_0.get('status_update')} (Prompt: {prompt_arquivo_nome})", flush=True)

        # 4. Executa LLM (Geração do Relatório)
        try:
            report_text = self._execute_llm(
                prompt_name=prompt_arquivo_nome,
                instrucoes_extras=job_data['instrucoes_extras'],
                model_name=model_name_yaml,
                user_email=job_data['usuario_executor'],
                job_id=job_id
            )
        except Exception as e:
            self._update_job_status(job_id, 'failed', error=str(e))
            raise e

        # 5. Salva no Blob Storage (CRUCIAL)
        # Adaptado do original: cria estrutura compatível com ReportHandler
        job_info_wrapper = {'data': job_data} 
        
        print(f"[{job_id}] Salvando relatório no Blob Storage...", flush=True)
        url = self.report_handler.save_report_to_blob(job_id, job_info_wrapper, report_text)
        
        if not url:
            print(f"[{job_id}] [ERRO] Falha ao salvar no Blob Storage.", flush=True)
        else:
            print(f"[{job_id}] Relatório salvo: {url}", flush=True)

        # 6. Atualiza estado e PAUSA para aprovação
        job_data['analysis_report'] = report_text
        job_data['report_blob_url'] = url
        job_data['status'] = 'pending_approval' # Pausa aqui
        self.jobs[job_id] = job_data

        return {
            'job_id': job_id,
            'status': 'pending_approval', # Retorna para o usuário avaliar
            'message': 'Relatório gerado e salvo. Aguardando aprovação para aplicar mudanças.',
            'report_url': url,
            'analysis_report': report_text
        }

    def approve_and_continue(self, job_id: str) -> Dict[str, Any]:
        """
        PASSO 2: Chamado pelo usuário após avaliar o relatório.
        Lê o relatório do Blob e executa o Step 2 (Aplicar Mudanças).
        """
        job_data = self.jobs.get(job_id)
        if not job_data:
            raise ValueError("Job ID não encontrado.")

        if job_data['status'] != 'pending_approval':
            raise ValueError(f"Job não está aguardando aprovação (Status atual: {job_data['status']})")

        print(f"[{job_id}] Aprovação recebida. Iniciando Step 1 (Aplicação)...", flush=True)

        # 1. Recupera configuração do YAML para o Step 1
        workflow_config = self.workflows_config.get(job_data['analysis_type'])
        steps = workflow_config.get('steps', [])
        
        if len(steps) < 2:
            # Se não tiver step 2, finaliza aqui
            self._update_job_status(job_id, 'completed')
            return {'job_id': job_id, 'status': 'completed', 'message': 'Não há passos adicionais.'}

        step_1 = steps[1] # Step de Aplicação
        params = step_1.get('params', {})
        prompt_arquivo_nome = params.get('tipo_analise') # Ex: aplicacao_de_mudancas
        model_name_yaml = step_1.get('model_name')

        # 2. Garante que temos o relatório (Lê do Blob se não estiver na memória)
        report_text = job_data.get('analysis_report')
        if not report_text and job_data.get('report_blob_url'):
            print(f"[{job_id}] Relatório não está em memória. Buscando do Blob...", flush=True)
            # Simulação de leitura do blob baseada no URL ou parâmetros
            report_text = self.report_handler.blob_storage.read_report(
                projeto=job_data['projeto'],
                analysis_type=job_data['analysis_type'],
                repository_type=job_data['repository_type'],
                repo_name=job_data['repo_name'],
                branch_name=job_data['branch_name'],
                analysis_name=job_data['analysis_name']
            )

        if not report_text:
            raise ValueError("Relatório original não encontrado para aplicar as mudanças.")

        # 3. Prepara o Prompt de Aplicação
        # O prompt de aplicação geralmente precisa do código + o relatório gerado anteriormente
        instrucoes_extras = (
            f"--- RELATÓRIO DE ANÁLISE PRÉVIA ---\n{report_text}\n\n"
            f"--- INSTRUÇÕES ADICIONAIS ---\n{job_data.get('instrucoes_extras', '')}"
        )

        print(f"[{job_id}] Executando Step 1: {step_1.get('status_update')} (Prompt: {prompt_arquivo_nome})", flush=True)

        # 4. Executa LLM (Aplicação das Mudanças)
        try:
            result_text = self._execute_llm(
                prompt_name=prompt_arquivo_nome,
                instrucoes_extras=instrucoes_extras,
                model_name=model_name_yaml,
                user_email=job_data['usuario_executor'],
                job_id=job_id
            )
        except Exception as e:
            self._update_job_status(job_id, 'failed', error=str(e))
            raise e

        # 5. Finaliza
        # Aqui você poderia salvar um novo artefato ou commitar código, mas vou retornar o resultado
        job_data['application_result'] = result_text
        self._update_job_status(job_id, 'completed')

        return {
            'job_id': job_id,
            'status': 'completed',
            'message': 'Mudanças aplicadas com sucesso.',
            'result': result_text
        }

    def _execute_llm(self, prompt_name, instrucoes_extras, model_name, user_email, job_id):
        """Helper centralizado para chamar o LLM."""
        try:
            prompt_base = carregar_prompt(prompt_name)
        except Exception:
            # Fallback se não achar arquivo
            prompt_base = f"Execute a tarefa: {prompt_name}"

        prompt_final = f"{prompt_base}\n\n{instrucoes_extras}" if instrucoes_extras else prompt_base

        llm_provider = create_provider(
            model_name=model_name,
            user_email=user_email,
            group_resolver=self.group_resolver
        )

        if hasattr(llm_provider, 'invoke'):
            response = llm_provider.invoke(prompt_final)
        else:
            resp_dict = llm_provider.executar_prompt(
                tipo_tarefa=prompt_name,
                prompt_principal=prompt_final,
                model_name=model_name,
                job_id=job_id
            )
            response = resp_dict.get('reposta_final', '')

        return response if isinstance(response, str) else str(response)

    def _update_job_status(self, job_id, status, error=None):
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = status
            if error:
                self.jobs[job_id]['error'] = error

    def get_status(self, job_id: str) -> Dict[str, Any]:
        return self.jobs.get(job_id)
