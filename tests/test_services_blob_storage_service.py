import pytest
from unittest.mock import Mock, patch
from services.blob_storage_service import BlobStorageService


class TestBlobStorageService:
    
    def setup_method(self):
        self.service = BlobStorageService()
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_success(self, mock_upload):
        mock_upload.return_value = "https://blob.storage/report.md"
        
        result = self.service.upload_report(
            report_text="Test report content",
            projeto="test-project",
            analysis_type="auditoria_testes",
            repository_type="github",
            repo_name="test/repo",
            branch_name="main",
            analysis_name="test-analysis"
        )
        
        assert result == "https://blob.storage/report.md"
        mock_upload.assert_called_once_with(
            "Test report content",
            "test-project",
            "auditoria_testes",
            "github",
            "test/repo",
            "main",
            "test-analysis"
        )
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_with_empty_content(self, mock_upload):
        mock_upload.return_value = "https://blob.storage/empty-report.md"
        
        result = self.service.upload_report(
            report_text="",
            projeto="empty-project",
            analysis_type="auditoria_testes",
            repository_type="gitlab",
            repo_name="empty/repo",
            branch_name="develop",
            analysis_name="empty-analysis"
        )
        
        assert result == "https://blob.storage/empty-report.md"
        mock_upload.assert_called_once()
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_with_unicode_content(self, mock_upload):
        mock_upload.return_value = "https://blob.storage/unicode-report.md"
        
        unicode_content = "# Unicode Report 🚀\n\n测试内容\n\n- Item 1 ✓\n- Item 2 🎯"
        
        result = self.service.upload_report(
            report_text=unicode_content,
            projeto="unicode-项目",
            analysis_type="auditoria_testes",
            repository_type="azure",
            repo_name="unicode/测试/repo",
            branch_name="feature/unicode",
            analysis_name="unicode-analysis-🔥"
        )
        
        assert result == "https://blob.storage/unicode-report.md"
        mock_upload.assert_called_once_with(
            unicode_content,
            "unicode-项目",
            "auditoria_testes",
            "azure",
            "unicode/测试/repo",
            "feature/unicode",
            "unicode-analysis-🔥"
        )
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_exception(self, mock_upload):
        mock_upload.side_effect = Exception("Blob storage connection failed")
        
        with pytest.raises(Exception, match="Blob storage connection failed"):
            self.service.upload_report(
                report_text="Test content",
                projeto="error-project",
                analysis_type="auditoria_testes",
                repository_type="github",
                repo_name="error/repo",
                branch_name="main",
                analysis_name="error-analysis"
            )
    
    @patch('services.blob_storage_service.read_report_from_blob')
    def test_read_report_success(self, mock_read):
        expected_content = "# Existing Report\n\nThis is an existing report content."
        mock_read.return_value = expected_content
        
        result = self.service.read_report(
            projeto="read-project",
            analysis_type="auditoria_testes",
            repository_type="github",
            repo_name="read/repo",
            branch_name="main",
            analysis_name="existing-analysis"
        )
        
        assert result == expected_content
        mock_read.assert_called_once_with(
            "read-project",
            "auditoria_testes",
            "github",
            "read/repo",
            "main",
            "existing-analysis"
        )
    
    @patch('services.blob_storage_service.read_report_from_blob')
    def test_read_report_not_found(self, mock_read):
        mock_read.side_effect = FileNotFoundError("Report not found")
        
        result = self.service.read_report(
            projeto="missing-project",
            analysis_type="auditoria_testes",
            repository_type="gitlab",
            repo_name="missing/repo",
            branch_name="main",
            analysis_name="missing-analysis"
        )
        
        assert result is None
    
    @patch('services.blob_storage_service.read_report_from_blob')
    def test_read_report_with_unicode_content(self, mock_read):
        unicode_content = "# Unicode Report 📊\n\n## 分析结果\n\n测试通过 ✅"
        mock_read.return_value = unicode_content
        
        result = self.service.read_report(
            projeto="unicode-读取项目",
            analysis_type="auditoria_testes",
            repository_type="azure",
            repo_name="unicode/读取/repo",
            branch_name="feature/unicode-读取",
            analysis_name="unicode-读取-analysis"
        )
        
        assert result == unicode_content
        assert "测试通过" in result
        assert "✅" in result
    
    @patch('services.blob_storage_service.read_report_from_blob')
    def test_read_report_general_exception(self, mock_read):
        mock_read.side_effect = Exception("Unexpected blob storage error")
        
        result = self.service.read_report(
            projeto="error-project",
            analysis_type="auditoria_testes",
            repository_type="github",
            repo_name="error/repo",
            branch_name="main",
            analysis_name="error-analysis"
        )
        
        assert result is None
    
    @patch('services.blob_storage_service.read_report_from_blob')
    def test_read_report_with_empty_parameters(self, mock_read):
        mock_read.return_value = "Empty params report"
        
        result = self.service.read_report(
            projeto="",
            analysis_type="",
            repository_type="",
            repo_name="",
            branch_name="",
            analysis_name=""
        )
        
        assert result == "Empty params report"
        mock_read.assert_called_once_with("", "", "", "", "", "")
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_with_large_content(self, mock_upload):
        mock_upload.return_value = "https://blob.storage/large-report.md"
        
        large_content = "# Large Report\n\n" + "Content line\n" * 10000
        
        result = self.service.upload_report(
            report_text=large_content,
            projeto="large-project",
            analysis_type="auditoria_testes",
            repository_type="github",
            repo_name="large/repo",
            branch_name="main",
            analysis_name="large-analysis"
        )
        
        assert result == "https://blob.storage/large-report.md"
        call_args = mock_upload.call_args[0]
        assert len(call_args[0]) > 100000  # Verify large content was passed
    
    @patch('services.blob_storage_service.upload_report_to_blob')
    def test_upload_report_with_special_characters_in_names(self, mock_upload):
        mock_upload.return_value = "https://blob.storage/special-report.md"
        
        result = self.service.upload_report(
            report_text="Special chars report",
            projeto="project-with-special-chars!@#$%",
            analysis_type="auditoria_testes",
            repository_type="github",
            repo_name="org/repo-with-special-chars!@#",
            branch_name="feature/special-chars-branch!@#",
            analysis_name="analysis-with-special-chars!@#$%"
        )
        
        assert result == "https://blob.storage/special-report.md"
        mock_upload.assert_called_once()