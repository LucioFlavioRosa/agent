import unittest
from azure_mcp.services.azure_logging_service import AzureLoggingService
import logging

class TestAzureLoggingService(unittest.TestCase):
    def setUp(self):
        # Não usar Application Insights nos testes
        self.logging_service = AzureLoggingService()

    def test_log_job_event_info(self):
        with self.assertLogs('azure_mcp', level='INFO') as cm:
            self.logging_service.log_job_event(
                job_id="job123",
                analysis_type="criacao_epicos_azure_devops",
                event="job_started",
                details={"user": "tester"}
            )
        self.assertTrue(any('job_started' in msg for msg in cm.output))

    def test_log_job_event_error(self):
        with self.assertLogs('azure_mcp', level='ERROR') as cm:
            self.logging_service.log_job_event(
                job_id="job456",
                analysis_type="revisor_tarefas",
                event="job_failed",
                details={"reason": "timeout"},
                level="error"
            )
        self.assertTrue(any('job_failed' in msg for msg in cm.output))

    def test_log_exception(self):
        try:
            raise ValueError("Test exception")
        except Exception as e:
            with self.assertLogs('azure_mcp', level='ERROR') as cm:
                self.logging_service.log_exception(
                    job_id="job789",
                    analysis_type="criacao_tarefas_azure_devops",
                    exception=e,
                    details={"step": 2}
                )
            self.assertTrue(any('exception' in msg for msg in cm.output))

if __name__ == "__main__":
    unittest.main()
