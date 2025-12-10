import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
import asyncio
from backend.app.services.project_state_service import ProjectStateService

def ensure_project_id(session_data: dict, usuario_executor: str = None, nome_projeto: str = None) -> str:
    project_id = session_data.get("project_id")
    if project_id and isinstance(project_id, str) and project_id.strip():
        return project_id
    try:
        estado_blob = None
        if usuario_executor and nome_projeto:
            try:
                estado_blob = asyncio.run(ProjectStateService.load_latest_state_from_blob(usuario_executor, nome_projeto=nome_projeto))
            except Exception as e:
                logging.getLogger("RedisSessionService").error(f"Erro ao buscar estado do Blob Storage para preencher project_id: {str(e)}")
        if estado_blob and estado_blob.get("project_id"):
            session_data["project_id"] = estado_blob["project_id"]
            return estado_blob["project_id"]
    except Exception as e:
        logging.getLogger("RedisSessionService").error(f"Erro inesperado ao tentar garantir project_id: {str(e)}")
    novo_id = str(uuid.uuid4())
    session_data["project_id"] = novo_id
    logging.getLogger("RedisSessionService").critical(f"project_id ausente, gerado novo UUID: {novo_id}")
    return novo_id

class RedisSessionService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=int(getattr(settings, 'REDIS_PORT', 6379)),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            db=int(getattr(settings, 'REDIS_DB', 0)),
            decode_responses=True,
            ssl=getattr(settings, 'REDIS_USE_SSL', True),
            ssl_cert_reqs=getattr(settings, 'REDIS_SSL_CERT_REQS', 'required')
        )
        self.session_ttl = int(getattr(settings, 'REDIS_SESSION_TTL', 86400))
        self.logger = logging.getLogger("RedisSessionService")

    def _serialize_session(self, session_data: dict) -> str:
        return json.dumps(session_data)

    def _deserialize_session(self, session_json: str) -> dict:
        return json.loads(session_json)

    def get_session_by_project_id(self, project_id: str) -> Optional[SessionData]:
        """
        Recupera a sessão do Redis e converte para o modelo SessionData.
        O Webhook precisa disso para acessar atributos como session.nome_projeto.
        """
        data = self.get_resumo_state(project_id)
        if data:
            try:
                # Converte o dicionário do Redis para o Objeto SessionData
                return SessionData(**data)
            except Exception as e:
                self.logger.error(f"Erro ao converter dados do Redis para SessionData: {e}")
                return None
        return None

    def update_report(self, project_id: str, report_data: Dict[str, Any]):
        """
        Atualiza os dados do relatório (ex: epicos_report) dentro da sessão principal no Redis.
        Isso garante que o próximo 'get_session' traga os dados atualizados.
        """
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        
        if session_json:
            try:
                session_data = self._deserialize_session(session_json)
                
                # Mescla os dados do relatório (ex: {"epicos_report": [...]}) na sessão
                session_data.update(report_data)
                
                # Atualiza timestamp
                session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
                
                # Salva de volta no Redis com TTL renovado
                self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
                self.logger.info(f"Relatório merged e atualizado no Redis para projeto {project_id}")
            except Exception as e:
                self.logger.error(f"Erro ao atualizar report no Redis: {e}")
                raise e
        else:
            msg = f"Tentativa de atualizar report para sessão inexistente no Redis: {project_id}"
            self.logger.error(msg)

    def create_session(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_id: str, extracted_text: Optional[str] = None, initial_state: Optional[Dict[str, Any]] = None) -> str:
        # --- OTIMIZAÇÃO: Busca única no Blob Storage se faltar algum dado ---
        blob_state_cached = None
        
        def get_blob_state_once():
            nonlocal blob_state_cached
            if blob_state_cached is None:
                try:
                    # Busca segura (retorna dict vazio se falhar ou não achar)
                    blob_state_cached = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                        usuario_executor or "",
                        project_id=project_id,
                        nome_projeto=nome_projeto
                    )) or {}
                except Exception as e:
                    self.logger.error(f"Erro ao buscar estado do Blob Storage: {str(e)}")
                    blob_state_cached = {}
            return blob_state_cached

        # 1. Garante usuario_executor
        if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
            state = get_blob_state_once()
            usuario_executor = state.get("usuario_executor")
            if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
                raise ValueError("Campo obrigatorio ausente: usuario_executor")

        # 2. Garante nome_projeto
        if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
            state = get_blob_state_once()
            nome_projeto = state.get("nome_projeto")
            if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
                raise ValueError("Campo obrigatorio ausente: nome_projeto")

        # 3. Garante project_id
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            # Usa os dados já validados para tentar recuperar o ID
            session_data_temp = initial_state if initial_state else {}
            session_data_temp["usuario_executor"] = usuario_executor
            session_data_temp["nome_projeto"] = nome_projeto
            
            # ensure_project_id também tem lógica de fallback, mas agora os dados base estão mais sólidos
            project_id = ensure_project_id(session_data_temp, usuario_executor, nome_projeto)

        # 4. Criação da Sessão no Redis
        key = f"project:{project_id}:resumo"
        created_at = datetime.utcnow().isoformat()
        last_saved_to_blob = datetime.utcnow().isoformat()
        
        session_data = {
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "last_saved_to_blob": last_saved_to_blob,
            "project_id": project_id,
            "ultima_analysis_type": analysis_type,
            "ultima_atualizacao": last_saved_to_blob
        }
        
        # Adiciona texto extraído se houver (útil para debug ou reprocessamento)
        if extracted_text:
             session_data["extracted_text"] = extracted_text

        # Adiciona estado inicial se houver (mescla com os dados base)
        if initial_state:
            session_data.update(initial_state)

        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def add_docx_file(self, project_id: str, blob_url: str):
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            try:
                session_data = self._deserialize_session(session_json)
                session_data["docx_url"] = blob_url
                session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
                self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
                self.logger.info(f"DOCX vinculado com sucesso ao projeto {project_id}")
            except Exception as e:
                self.logger.error(f"Erro ao atualizar sessão com DOCX no Redis: {e}")
        else:
            self.logger.warning(f"Tentativa de adicionar DOCX a uma sessão inexistente: {project_id}")

    def create_report_state(self, project_id: str, report_type: str, state_data: Dict[str, Any]):
        key = f"project:{project_id}:report:{report_type}"
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(state_data))

    def update_report_state(self, project_id: str, report_type: str, state_data: Dict[str, Any]):
        key = f"project:{project_id}:report:{report_type}"
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(state_data))

    def get_report_state(self, project_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        key = f"project:{project_id}:report:{report_type}"
        session_json = self.redis_client.get(key)
        if session_json:
            return self._deserialize_session(session_json)
        return None

    def get_resumo_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            self.logger.info(f"Resumo do projeto {project_id} encontrado no Redis.")
            return self._deserialize_session(session_json)
        self.logger.info(f"Resumo do projeto {project_id} não encontrado no Redis.")
        return None

    def restore_session_from_state(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_state: Dict[str, Any]) -> str:
        project_id = project_state.get("project_id")
        nome_projeto_val = project_state.get("nome_projeto")
        usuario_executor_val = project_state.get("usuario_executor")
        
        # --- NOVA GARANTIA project_id ---
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            session_data = dict(project_state)
            session_data["usuario_executor"] = usuario_executor or usuario_executor_val
            session_data["nome_projeto"] = nome_projeto or nome_projeto_val
            pid = ensure_project_id(session_data, session_data["usuario_executor"], session_data["nome_projeto"])
            project_id = pid
            
        # Otimização: Se já temos os dados no 'project_state', evitamos buscar no blob de novo
        if (not nome_projeto_val) or (not usuario_executor_val):
             try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
                if blob_state:
                    nome_projeto_val = nome_projeto_val or blob_state.get("nome_projeto")
                    usuario_executor_val = usuario_executor_val or blob_state.get("usuario_executor")
             except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos: {str(e)}")

        if not nome_projeto_val or not usuario_executor_val or not project_id:
            raise ValueError("Campos obrigatórios ausentes ao restaurar sessão: usuario_executor, nome_projeto, project_id")
            
        key = f"project:{project_id}:resumo"
        session_data = dict(project_state)
        session_data["usuario_executor"] = usuario_executor_val
        session_data["nome_projeto"] = nome_projeto_val
        session_data["analysis_type"] = analysis_type
        session_data["ultima_analysis_type"] = analysis_type
        session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
        session_data["project_id"] = project_id
        
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id
