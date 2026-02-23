import pytest
from backend.app.utils.blob_storage_helper import sanitize_email, build_blob_path

class TestBlobStorageHelper:
    def test_sanitize_email_removes_invalid_chars(self):
        email = 'user.name+test@example.com'
        sanitized = sanitize_email(email)
        assert '@' not in sanitized
        assert '.' not in sanitized
        assert '+' not in sanitized
        assert '/' not in sanitized
        assert '\\' not in sanitized
        assert sanitized == 'usernametestexamplecom'

    def test_sanitize_email_handles_empty_string(self):
        sanitized = sanitize_email('')
        assert sanitized == ''

    def test_build_blob_path_success(self):
        company_id = '123'
        email = 'user.name@example.com'
        project_id = '456'
        job_id = '789'
        filename = 'documento_recebido.docx'
        path = build_blob_path(company_id, email, project_id, job_id, filename)
        assert path == '123/usernametestexamplecom/456/789/documento_recebido.docx'

    def test_build_blob_path_raises_on_empty_params(self):
        with pytest.raises(ValueError):
            build_blob_path('', 'email', 'pid', 'jid', 'file.docx')
        with pytest.raises(ValueError):
            build_blob_path('cid', '', 'pid', 'jid', 'file.docx')
        with pytest.raises(ValueError):
            build_blob_path('cid', 'email', '', 'jid', 'file.docx')
        with pytest.raises(ValueError):
            build_blob_path('cid', 'email', 'pid', '', 'file.docx')
        with pytest.raises(ValueError):
            build_blob_path('cid', 'email', 'pid', 'jid', '')
