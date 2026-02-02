import unittest
from services.simplified_workflow_service import SimplifiedWorkflowService
from services.analysis_config import AnalysisConfig

class TestSimplifiedWorkflowService(unittest.TestCase):
    def setUp(self):
        self.config = AnalysisConfig(repository_url='https://github.com/example/repo', analysis_type='clean_code')
        self.service = SimplifiedWorkflowService(self.config)

    def test_run_analysis_returns_report(self):
        report = self.service.run_analysis()
        self.assertIsInstance(report, dict)
        self.assertIn('summary', report)
        self.assertIn('issues', report)

    def test_analysis_config_properties(self):
        self.assertEqual(self.config.repository_url, 'https://github.com/example/repo')
        self.assertEqual(self.config.analysis_type, 'clean_code')

if __name__ == '__main__':
    unittest.main()
