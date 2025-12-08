import pytest
from unittest.mock import MagicMock
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.models.session_models import SessionData
from datetime import datetime
import uuid

@pytest.fixture
def redis_service(monkeypatch):
    service = RedisSessionService()
    service.redis_client = MagicMock()
    service.session_ttl = 86400
    return service

@pytest.fixture
def project_state_full():
    return {
        "usuario_executor": "user1",
        "nome_projeto": "ProjetoTeste",
        "analysis_type": "tipo1",
        "created_at": datetime.utcnow().isoformat(),
        "last_saved_to_blob": datetime.utcnow().isoformat(),
        "docx_files": ["url1"],
        "project_id": str(uuid.uuid4()),
        "epicos_report": [{"id": 1}],
        "features_report": [{"id": 2}],
        "times_descricao_report": [{"id": 3}],
        "alocacao_times_report": [{"id": 4}],
        "premissas_riscos_report": [{"id": 5}]
    }

def test_restore_session_from_state_preserves_reports(redis_service, project_state_full):
    usuario_executor = "user1"
    nome_projeto = "ProjetoTeste"
    analysis_type = "tipo1"
    project_state = dict(project_state_full)
    project_id = project_state["project_id"]
    redis_service.redis_client.setex = MagicMock()
    result_project_id = redis_service.restore_session_from_state(
        usuario_executor, nome_projeto, analysis_type, project_state
    )
    assert result_project_id == project_id
    args, kwargs = redis_service.redis_client.setex.call_args
    saved_data = args[1]
    import json
    session_data = json.loads(saved_data)
    assert session_data["epicos_report"] == [{"id": 1}]
    assert session_data["features_report"] == [{"id": 2}]
    assert session_data["times_descricao_report"] == [{"id": 3}]
    assert session_data["alocacao_times_report"] == [{"id": 4}]
    assert session_data["premissas_riscos_report"] == [{"id": 5}]

def test_create_session_initializes_reports_as_empty_lists(redis_service):
    usuario_executor = "user2"
    nome_projeto = "NovoProjeto"
    analysis_type = "tipo2"
    project_id = str(uuid.uuid4())
    redis_service.redis_client.exists = MagicMock(return_value=False)
    redis_service.redis_client.setex = MagicMock()
    redis_service.create_session(
        usuario_executor, nome_projeto, analysis_type, project_id, extracted_text=None, initial_state=None
    )
    args, kwargs = redis_service.redis_client.setex.call_args
    saved_data = args[1]
    import json
    session_data = json.loads(saved_data)
    assert session_data["epicos_report"] == []
    assert session_data["features_report"] == []
    assert session_data["times_descricao_report"] == []
    assert session_data["alocacao_times_report"] == []
    assert session_data["premissas_riscos_report"] == []

def test_update_report_only_updates_one_field(redis_service, project_state_full):
    project_id = project_state_full["project_id"]
    session_json = dict(project_state_full)
    redis_service.redis_client.get = MagicMock(return_value=SessionData(**session_json).json())
    redis_service.redis_client.setex = MagicMock()
    report_data = {"alocacao_times_report": [{"id": 999, "novo": True}]}
    redis_service.update_report(project_id, report_data)
    args, kwargs = redis_service.redis_client.setex.call_args
    saved_data = args[1]
    import json
    session_data = json.loads(saved_data)
    assert session_data["alocacao_times_report"] == [{"id": 999, "novo": True}]
    assert session_data["epicos_report"] == [{"id": 1}]
    assert session_data["features_report"] == [{"id": 2}]
    assert session_data["times_descricao_report"] == [{"id": 3}]
    assert session_data["premissas_riscos_report"] == [{"id": 5}]
