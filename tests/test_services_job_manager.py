import pytest
from unittest.mock import Mock, patch
from services.job_manager import JobManager


class TestJobManager:
    
    def setup_method(self):
        self.mock_job_store = Mock()
        self.job_manager = JobManager(self.mock_job_store)
    
    def test_init_with_valid_job_store(self):
        assert self.job_manager.job_store == self.mock_job_store
    
    def test_init_with_none_job_store_raises_error(self):
        with pytest.raises(TypeError):
            JobManager(None)
    
    def test_get_job_success(self):
        expected_job = {"id": "test-123", "status": "running"}
        self.mock_job_store.get_job.return_value = expected_job
        
        result = self.job_manager.get_job("test-123")
        
        assert result == expected_job
        self.mock_job_store.get_job.assert_called_once_with("test-123")
    
    def test_get_job_not_found(self):
        self.mock_job_store.get_job.return_value = None
        
        result = self.job_manager.get_job("nonexistent")
        
        assert result is None
        self.mock_job_store.get_job.assert_called_once_with("nonexistent")
    
    def test_get_job_with_empty_string_id(self):
        self.mock_job_store.get_job.return_value = None
        
        result = self.job_manager.get_job("")
        
        assert result is None
        self.mock_job_store.get_job.assert_called_once_with("")
    
    def test_update_job_success(self):
        job_data = {"id": "test-456", "status": "completed", "result": "success"}
        
        self.job_manager.update_job("test-456", job_data)
        
        self.mock_job_store.set_job.assert_called_once_with("test-456", job_data)
    
    def test_update_job_with_empty_data(self):
        job_data = {}
        
        self.job_manager.update_job("test-789", job_data)
        
        self.mock_job_store.set_job.assert_called_once_with("test-789", job_data)
    
    def test_update_job_with_none_data_raises_error(self):
        with pytest.raises(TypeError):
            self.job_manager.update_job("test-123", None)
    
    def test_update_job_status_success(self):
        existing_job = {"id": "test-111", "status": "running", "data": "some_data"}
        self.mock_job_store.get_job.return_value = existing_job
        
        self.job_manager.update_job_status("test-111", "completed")
        
        expected_updated_job = {"id": "test-111", "status": "completed", "data": "some_data"}
        self.mock_job_store.set_job.assert_called_once_with("test-111", expected_updated_job)
    
    def test_update_job_status_job_not_found(self):
        self.mock_job_store.get_job.return_value = None
        
        self.job_manager.update_job_status("nonexistent", "failed")
        
        self.mock_job_store.set_job.assert_not_called()
    
    def test_update_job_status_with_invalid_status(self):
        existing_job = {"id": "test-222", "status": "running"}
        self.mock_job_store.get_job.return_value = existing_job
        
        self.job_manager.update_job_status("test-222", "")
        
        expected_updated_job = {"id": "test-222", "status": ""}
        self.mock_job_store.set_job.assert_called_once_with("test-222", expected_updated_job)
    
    @patch('services.job_manager.traceback.print_exc')
    def test_handle_job_error_success(self, mock_traceback):
        existing_job = {"id": "test-333", "status": "running"}
        self.mock_job_store.get_job.return_value = existing_job
        
        test_error = Exception("Test error message")
        self.job_manager.handle_job_error("test-333", test_error, "processing")
        
        expected_updated_job = {
            "id": "test-333",
            "status": "failed",
            "error_details": "Erro fatal durante a etapa 'processing': Test error message"
        }
        self.mock_job_store.set_job.assert_called_once_with("test-333", expected_updated_job)
        mock_traceback.assert_called_once()
    
    @patch('services.job_manager.traceback.print_exc')
    def test_handle_job_error_job_not_found(self, mock_traceback):
        self.mock_job_store.get_job.return_value = None
        
        test_error = ValueError("Validation error")
        self.job_manager.handle_job_error("nonexistent", test_error, "validation")
        
        self.mock_job_store.set_job.assert_not_called()
        mock_traceback.assert_called_once()
    
    @patch('services.job_manager.traceback.print_exc')
    def test_handle_job_error_redis_failure(self, mock_traceback):
        existing_job = {"id": "test-444", "status": "running"}
        self.mock_job_store.get_job.return_value = existing_job
        self.mock_job_store.set_job.side_effect = Exception("Redis connection failed")
        
        test_error = RuntimeError("Processing failed")
        self.job_manager.handle_job_error("test-444", test_error, "execution")
        
        mock_traceback.assert_called_once()
    
    def test_handle_job_error_with_unicode_error_message(self):
        existing_job = {"id": "test-555", "status": "running"}
        self.mock_job_store.get_job.return_value = existing_job
        
        test_error = Exception("Unicode error: 测试错误 🚨")
        
        with patch('services.job_manager.traceback.print_exc'):
            self.job_manager.handle_job_error("test-555", test_error, "unicode_processing")
        
        expected_error_message = "Erro fatal durante a etapa 'unicode_processing': Unicode error: 测试错误 🚨"
        expected_updated_job = {
            "id": "test-555",
            "status": "failed",
            "error_details": expected_error_message
        }
        self.mock_job_store.set_job.assert_called_once_with("test-555", expected_updated_job)
    
    def test_handle_job_error_with_none_error(self):
        existing_job = {"id": "test-666", "status": "running"}
        self.mock_job_store.get_job.return_value = existing_job
        
        with patch('services.job_manager.traceback.print_exc'):
            self.job_manager.handle_job_error("test-666", None, "null_processing")
        
        expected_error_message = "Erro fatal durante a etapa 'null_processing': None"
        expected_updated_job = {
            "id": "test-666",
            "status": "failed",
            "error_details": expected_error_message
        }
        self.mock_job_store.set_job.assert_called_once_with("test-666", expected_updated_job)