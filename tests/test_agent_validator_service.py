import unittest

class AgentValidatorService:
    VALID_AGENTS = {'review', 'improve'}

    @staticmethod
    def is_valid(agent_type):
        return agent_type in AgentValidatorService.VALID_AGENTS

class TestAgentValidatorService(unittest.TestCase):
    def test_valid_agents(self):
        self.assertTrue(AgentValidatorService.is_valid('review'))
        self.assertTrue(AgentValidatorService.is_valid('improve'))

    def test_invalid_agents(self):
        self.assertFalse(AgentValidatorService.is_valid('invalid'))
        self.assertFalse(AgentValidatorService.is_valid('delete'))
        self.assertFalse(AgentValidatorService.is_valid(''))
        self.assertFalse(AgentValidatorService.is_valid(None))

    def test_edge_cases(self):
        self.assertFalse(AgentValidatorService.is_valid(None))
        self.assertFalse(AgentValidatorService.is_valid(''))
        self.assertFalse(AgentValidatorService.is_valid(' '))

if __name__ == '__main__':
    unittest.main()
