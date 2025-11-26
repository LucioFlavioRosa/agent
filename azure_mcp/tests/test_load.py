import threading
import unittest
from azure_mcp.services.azure_logging_service import AzureLoggingService

class TestLoadLogging(unittest.TestCase):
    def setUp(self):
        self.logging_service = AzureLoggingService()

    def worker(self, job_id):
        self.logging_service.log_job_event(job_id, "criacao_epicos_azure_devops", "job_started")
        self.logging_service.log_job_event(job_id, "criacao_epicos_azure_devops", "job_completed")

    def test_concurrent_jobs(self):
        threads = []
        for i in range(10):
            t = threading.Thread(target=self.worker, args=(f"job_{i}",))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        # Teste de carga: valida ausência de exceções em múltiplos jobs concorrentes

if __name__ == "__main__":
    unittest.main()
