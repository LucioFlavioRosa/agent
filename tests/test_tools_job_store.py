import pytest
import json
from unittest.mock import Mock, patch
from tools.job_store import RedisJobStore


class TestRedisJobStore:
    
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'})
    @patch('tools.job_store.redis.from_url')
    def setup_method(self, mock_redis_from_url):
        self.mock_redis_client = Mock()
        mock_redis_from_url.return_value = self.mock_redis_client
        self.job_store = RedisJobStore()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_redis_url_raises_error(self):
        with pytest.raises(ValueError, match="A variável de ambiente REDIS_URL não foi configurada"):
            RedisJobStore()
    
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'})
    @patch('tools.job_store.redis.from_url')
    def test_init_with_valid_redis_url(self, mock_redis_from_url):
        mock_redis_client = Mock()
        mock_redis_from_url.return_value = mock_redis_client
        
        job_store = RedisJobStore()
        
        assert job_store.redis_client == mock_redis_client
        assert job_store.JOB_KEY_PREFIX == "mcp_job"
        mock_redis_from_url.assert_called_once_with('redis://localhost:6379', decode_responses=True)
    
    def test_set_job_success(self):
        job_data = {"id": "test-123", "status": "running", "data": {"key": "value"}}
        
        self.job_store.set_job("test-123", job_data)
        
        expected_key = "mcp_job:test-123"
        expected_json = json.dumps(job_data)
        self.mock_redis_client.set.assert_called_once_with(expected_key, expected_json, ex=86400)
    
    def test_set_job_with_custom_ttl(self):
        job_data = {"id": "test-456", "status": "completed"}
        custom_ttl = 3600
        
        self.job_store.set_job("test-456", job_data, ttl=custom_ttl)
        
        expected_key = "mcp_job:test-456"
        expected_json = json.dumps(job_data)
        self.mock_redis_client.set.assert_called_once_with(expected_key, expected_json, ex=custom_ttl)
    
    def test_set_job_with_empty_data(self):
        job_data = {}
        
        self.job_store.set_job("empty-job", job_data)
        
        expected_key = "mcp_job:empty-job"
        expected_json = json.dumps(job_data)
        self.mock_redis_client.set.assert_called_once_with(expected_key, expected_json, ex=86400)
    
    def test_set_job_with_unicode_data(self):
        job_data = {"message": "测试数据", "emoji": "🚀", "status": "processing"}
        
        self.job_store.set_job("unicode-job", job_data)
        
        expected_key = "mcp_job:unicode-job"
        expected_json = json.dumps(job_data)
        self.mock_redis_client.set.assert_called_once_with(expected_key, expected_json, ex=86400)
    
    def test_set_job_redis_error(self):
        import redis
        self.mock_redis_client.set.side_effect = redis.exceptions.RedisError("Connection failed")
        
        job_data = {"id": "error-job", "status": "failed"}
        
        self.job_store.set_job("error-job", job_data)
        
        self.mock_redis_client.set.assert_called_once()
    
    def test_set_job_with_non_serializable_data(self):
        class NonSerializable:
            pass
        
        job_data = {"object": NonSerializable()}
        
        with pytest.raises(TypeError):
            self.job_store.set_job("invalid-job", job_data)
    
    def test_get_job_success(self):
        job_data = {"id": "test-789", "status": "completed", "result": "success"}
        self.mock_redis_client.get.return_value = json.dumps(job_data)
        
        result = self.job_store.get_job("test-789")
        
        assert result == job_data
        expected_key = "mcp_job:test-789"
        self.mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_get_job_not_found(self):
        self.mock_redis_client.get.return_value = None
        
        result = self.job_store.get_job("nonexistent")
        
        assert result is None
        expected_key = "mcp_job:nonexistent"
        self.mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_get_job_with_empty_string_id(self):
        self.mock_redis_client.get.return_value = None
        
        result = self.job_store.get_job("")
        
        assert result is None
        expected_key = "mcp_job:"
        self.mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_get_job_with_unicode_content(self):
        job_data = {"message": "Unicode test: 测试 🎯", "status": "completed"}
        self.mock_redis_client.get.return_value = json.dumps(job_data, ensure_ascii=False)
        
        result = self.job_store.get_job("unicode-job")
        
        assert result == job_data
        assert result["message"] == "Unicode test: 测试 🎯"
    
    def test_get_job_invalid_json(self):
        self.mock_redis_client.get.return_value = "invalid json data"
        
        with pytest.raises(json.JSONDecodeError):
            self.job_store.get_job("invalid-json-job")
    
    def test_get_job_redis_error(self):
        import redis
        self.mock_redis_client.get.side_effect = redis.exceptions.RedisError("Connection timeout")
        
        result = self.job_store.get_job("error-job")
        
        assert result is None
    
    def test_get_job_with_complex_nested_data(self):
        complex_data = {
            "id": "complex-job",
            "nested": {
                "level1": {
                    "level2": {
                        "array": [1, 2, 3, {"key": "value"}],
                        "boolean": True,
                        "null_value": None
                    }
                }
            },
            "status": "processing"
        }
        self.mock_redis_client.get.return_value = json.dumps(complex_data)
        
        result = self.job_store.get_job("complex-job")
        
        assert result == complex_data
        assert result["nested"]["level1"]["level2"]["array"][3]["key"] == "value"
        assert result["nested"]["level1"]["level2"]["boolean"] is True
        assert result["nested"]["level1"]["level2"]["null_value"] is None
    
    def test_job_key_prefix_format(self):
        self.job_store.set_job("format-test", {"test": "data"})
        
        call_args = self.mock_redis_client.set.call_args[0]
        key_used = call_args[0]
        
        assert key_used.startswith("mcp_job:")
        assert key_used == "mcp_job:format-test"