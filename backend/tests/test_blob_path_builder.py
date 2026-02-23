import pytest
from slugify import slugify

# Função a ser testada

def build_blob_path(company_id, email, project_id, job_id, filename):
    """
    Monta o caminho do blob conforme regras:
    company_id/email/project_id/job_id/{filename}
    Sanitiza email e filename.
    """
    sanitized_email = slugify(email)
    sanitized_filename = slugify(filename, separator='-')
    return f"{slugify(company_id)}/{sanitized_email}/{slugify(project_id)}/{slugify(job_id)}/{sanitized_filename}"


def test_build_path_success():
    path = build_blob_path("123", "user@example.com", "proj456", "job789", "relatorio.md")
    assert path == "123/user-example-com/proj456/job789/relatorio-md"


def test_build_path_email_sanitization():
    path = build_blob_path("abc", "john.doe@company.co", "proj", "job", "comentario_extra.md")
    assert path == "abc/john-doe-company-co/proj/job/comentario-extra-md"


def test_build_path_special_chars():
    path = build_blob_path("!@#", "user+test@domain.com", "pr*oj", "jo$b", "documento_recebido.docx")
    assert path == "user-test-domain-com/pr-oj/jo-b/documento-recebido-docx"
