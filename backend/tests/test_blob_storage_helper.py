import pytest
from backend.app.utils.blob_storage_helper import sanitize_email, build_blob_path

def test_sanitize_email():
    assert sanitize_email('user@example.com') == 'user_example_com'
    assert sanitize_email('user.name+test@domain.co.uk') == 'user_name_test_domain_co_uk'
    assert sanitize_email('user@domain') == 'user_domain'
    assert sanitize_email('user+foo.bar@domain.com') == 'user_foo_bar_domain_com'
    assert sanitize_email('user@domain.com.br') == 'user_domain_com_br'

def test_build_blob_path():
    company_id = 'comp123'
    email = 'user.name+test@domain.co.uk'
    project_id = 'proj456'
    job_id = 'job789'
    filename = 'documento_recebido.docx'
    sanitized = sanitize_email(email)
    expected_path = f"{company_id}/{sanitized}/{project_id}/{job_id}/{filename}"
    assert build_blob_path(company_id, email, project_id, job_id, filename) == expected_path
    # Testa com caracteres especiais
    email2 = 'user+foo.bar@domain.com'
    sanitized2 = sanitize_email(email2)
    expected_path2 = f"{company_id}/{sanitized2}/{project_id}/{job_id}/{filename}"
    assert build_blob_path(company_id, email2, project_id, job_id, filename) == expected_path2
    # Testa com email simples
    email3 = 'user@domain'
    sanitized3 = sanitize_email(email3)
    expected_path3 = f"{company_id}/{sanitized3}/{project_id}/{job_id}/{filename}"
    assert build_blob_path(company_id, email3, project_id, job_id, filename) == expected_path3
