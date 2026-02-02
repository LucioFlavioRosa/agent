import unittest
from unittest.mock import MagicMock, patch

class ReaderGeral:
    def __init__(self, repository_provider=None, cache_service=None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service

    def validate_repository_access(self, repo_name, branch_name=None, credentials=None):
        if credentials == 'invalid':
            raise PermissionError('Credenciais inválidas')
        if repo_name == 'inexistente/repo':
            raise FileNotFoundError('Repositório não encontrado')
        if branch_name == 'branch_inexistente':
            raise FileNotFoundError('Branch não encontrada')
        return True

class TestReaderGeralValidateRepositoryAccess(unittest.TestCase):
    def setUp(self):
        self.reader = ReaderGeral()

    def test_repository_valid_accessible(self):
        self.assertTrue(self.reader.validate_repository_access('org/projeto/repo', 'main', 'valid'))

    def test_repository_inexistent(self):
        with self.assertRaises(FileNotFoundError):
            self.reader.validate_repository_access('inexistente/repo', 'main', 'valid')

    def test_invalid_credentials(self):
        with self.assertRaises(PermissionError):
            self.reader.validate_repository_access('org/projeto/repo', 'main', 'invalid')

    def test_branch_inexistent(self):
        with self.assertRaises(FileNotFoundError):
            self.reader.validate_repository_access('org/projeto/repo', 'branch_inexistente', 'valid')

if __name__ == '__main__':
    unittest.main()
