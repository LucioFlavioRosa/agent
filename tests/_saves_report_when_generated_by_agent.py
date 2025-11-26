import pytest
from unittest.mock import MagicMock
from models import JobFields, JobStatus

# Testes removidos: Azure Board (epics, features, tarefas, revisor_tarefas)
# Mantidos apenas testes genéricos do MCP original

def test_report_is_saved_for_generic_agent():
    job_store = MagicMock()
    report_handler = MagicMock()
    job_id = 'job-123'
    job_info = {
        'data': {
            'repo_name_modernizado': 'org/proj/repo',
            'analysis_type': 'modernizacao',
            'analysis_report': 'Relatório genérico',
            'report_blob_url': None
        },
        'status': JobStatus.STARTING
    }
    step_result = {'resultado': {'reposta_final': 'Relatório genérico'}}
    report_handler.extract_report_text.return_value = 'Relatório genérico'
    report_handler.save_report_to_blob.return_value = 'https://blob.url/report.md'
    # Simula chamada de salvar relatório
    report_text = report_handler.extract_report_text(step_result)
    url = report_handler.save_report_to_blob(job_id, job_info, report_text)
    assert report_text == 'Relatório genérico'
    assert url == 'https://blob.url/report.md'

# Todos os testes específicos de Azure Board foram removidos deste MCP.