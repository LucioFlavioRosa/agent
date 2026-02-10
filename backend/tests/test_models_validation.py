import pytest
from pydantic import ValidationError
from backend.app.models.user_models import UserContext
from backend.app.models.project_models import ProjectListItem
from backend.app.models.job_models import JobData
from backend.app.models.session_models import SessionData
from backend.app.models.audit_models import FrontendToBackendPayload, BackendToFrontendPayload
from backend.app.models.mcp_models import MCPStartAnalysisPayload, MCPStartAnalysisResponse
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.models.project_state_models import EstadoResumoProjeto, EstadoEpicos, EstadoEpicosTimeline, EstadoFeatures, EstadoAlocacaoTimes, EstadoPremissasRiscos, EstadoCompletoProjetoResponse
from backend.app.models.mcp_config_models import MCPAgentConfig, MCPConfigRegistry
from backend.app.models.docx_models import UploadDocxResponse
from datetime import datetime


def test_user_context_valid():
    uc = UserContext(email="user@example.com", empresa="Peers")
    assert uc.email == "user@example.com"
    assert uc.empresa == "Peers"


def test_project_list_item_valid():
    item = ProjectListItem(
        nome_projeto="Projeto Teste",
        created_at=datetime.utcnow()
    )
    assert item.nome_projeto == "Projeto Teste"


def test_job_data_valid():
    jd = JobData(
        job_id="job123",
        project_id="proj456",
        analysis_type="epicos",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        request_timestamp=datetime.utcnow()
    )
    assert jd.job_id == "job123"


def test_session_data_valid():
    sd = SessionData(
        usuario_executor="user",
        nome_projeto="Projeto",
        analysis_type="epicos",
        created_at=datetime.utcnow(),
        last_saved_to_blob=datetime.utcnow(),
        project_id="proj123"
    )
    assert sd.nome_projeto == "Projeto"


def test_frontend_to_backend_payload_valid():
    payload = FrontendToBackendPayload(
        endpoint="/api/test",
        method="POST",
        payload_data={"foo": "bar"}
    )
    assert payload.endpoint == "/api/test"


def test_backend_to_frontend_payload_valid():
    payload = BackendToFrontendPayload(
        endpoint="/api/test",
        status_code=200,
        response_data={"foo": "bar"}
    )
    assert payload.status_code == 200


def test_mcp_start_analysis_payload_valid():
    payload = MCPStartAnalysisPayload(
        project_id="proj123",
        analysis_type="epicos",
        job_id="job456"
    )
    assert payload.project_id == "proj123"


def test_mcp_webhook_payload_valid():
    webhook = MCPWebhookPayload(
        job_id="job789",
        status="in_progress"
    )
    assert webhook.status == "in_progress"


def test_estado_resumo_projeto_valid():
    estado = EstadoResumoProjeto(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_mcp_agent_config_valid():
    agent = MCPAgentConfig(
        agent_name="mcp1",
        mcp_url="http://mcp1.local"
    )
    assert agent.agent_name == "mcp1"


def test_upload_docx_response_valid():
    resp = UploadDocxResponse(
        message="Upload feito",
        blob_url="http://blob.local/file.docx",
        project_id="proj123"
    )
    assert resp.message == "Upload feito"


def test_invalid_job_data_empty_fields():
    with pytest.raises(ValidationError):
        JobData(
            job_id="",
            project_id="",
            analysis_type="",
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request_timestamp=datetime.utcnow()
        )


def test_estado_epicos_valid():
    estado = EstadoEpicos(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_estado_epicos_timeline_valid():
    estado = EstadoEpicosTimeline(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_estado_features_valid():
    estado = EstadoFeatures(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_estado_alocacao_times_valid():
    estado = EstadoAlocacaoTimes(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_estado_premissas_riscos_valid():
    estado = EstadoPremissasRiscos(
        nome_projeto="Projeto",
        created_at=datetime.utcnow(),
        ultima_atualizacao=datetime.utcnow()
    )
    assert estado.nome_projeto == "Projeto"


def test_estado_completo_projeto_response_valid():
    response = EstadoCompletoProjetoResponse()
    assert response.resumo is None
    assert response.epicos is None
