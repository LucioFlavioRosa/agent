import pytest
from backend.app.utils.blob_storage_helper import sanitize_email, build_blob_path

@pytest.mark.parametrize("email,expected", [
    ("user@example.com", "user_example_com"),
    ("user+test@example.com", "user_test_example_com"),
    ("user.name+tag@domain.co.uk", "user_name_tag_domain_co_uk"),
    ("user@domain", "user_domain"),
    ("user.name@domain.com", "user_name_domain_com")
])
def test_sanitize_email(email, expected):
    assert sanitize_email(email) == expected

@pytest.mark.parametrize("company_id,email,project_id,job_id,filename,expected", [
    ("comp123", "user@example.com", "proj456", "job789", "doc.docx", "comp123/user_example_com/proj456/job789/doc.docx"),
    ("comp123", "user.name+tag@domain.co.uk", "proj456", "job789", "file.pdf", "comp123/user_name_tag_domain_co_uk/proj456/job789/file.pdf"),
    ("comp123", "user@domain", "proj456", "job789", "report.txt", "comp123/user_domain/proj456/job789/report.txt")
])
def test_build_blob_path(company_id, email, project_id, job_id, filename, expected):
    assert build_blob_path(company_id, email, project_id, job_id, filename) == expected
