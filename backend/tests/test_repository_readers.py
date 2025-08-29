import pytest
from unittest.mock import Mock, patch, MagicMock
from tools.github_reader import GitHubRepositoryReader
from tools.repository_provider_factory import (
    get_repository_provider,
    get_repository_provider_explicit,
    detect_repository_type
)
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from domain.interfaces.repository_provider_interface import IRepositoryProvider

class TestRepositoryProviderFactory:
    """
    Testes para a factory de provedores de repositório.
    
    Esta classe testa a lógica de detecção automática de provedores
    baseada em padrões de nomenclatura de repositórios.
    """
    
    def test_detect_github_repository(self):
        """
        Testa detecção de repositórios GitHub com padrões típicos.
        
        Repositórios GitHub seguem o padrão 'org/repo' e são o tipo
        mais comum, servindo como fallback padrão.
        """
        github_repos = [
            "microsoft/vscode",
            "facebook/react",
            "google/tensorflow",
            "apache/kafka",
            "kubernetes/kubernetes"
        ]
        
        for repo_name in github_repos:
            provider = get_repository_provider(repo_name)
            assert isinstance(provider, GitHubRepositoryProvider), f"Falhou para {repo_name}"
            assert detect_repository_type(repo_name) == 'github'
    
    def test_detect_gitlab_repository(self):
        """
        Testa detecção de repositórios GitLab baseada em heurísticas.
        
        GitLab é detectado por indicadores como 'gitlab' no nome,
        padrões de nomenclatura com hífens longos, sufixos específicos.
        """
        gitlab_repos = [
            "gitlab-org/gitlab",
            "gitlab-com/gitlab-runner",
            "empresa-desenvolvimento-org/projeto-interno",
            "minha-organizacao-group/sistema-principal",
            "tech-team-org/microservico-auth"
        ]
        
        for repo_name in gitlab_repos:
            provider = get_repository_provider(repo_name)
            assert isinstance(provider, GitLabRepositoryProvider), f"Falhou para {repo_name}"
            assert detect_repository_type(repo_name) == 'gitlab'
    
    def test_detect_azure_devops_repository(self):
        """
        Testa detecção de repositórios Azure DevOps com 3 partes.
        
        Azure DevOps usa formato 'organization/project/repository'
        que é facilmente distinguível por ter 3 partes.
        """
        azure_repos = [
            "myorg/myproject/myrepo",
            "empresa/sistema-vendas/api-backend",
            "dev-team/projeto-mobile/app-android",
            "corporation/division/service-auth"
        ]
        
        for repo_name in azure_repos:
            provider = get_repository_provider(repo_name)
            assert isinstance(provider, AzureRepositoryProvider), f"Falhou para {repo_name}"
            assert detect_repository_type(repo_name) == 'azure'
    
    def test_explicit_provider_creation(self):
        """
        Testa criação explícita de provedores por tipo.
        
        Função útil quando se conhece o tipo ou quando a detecção
        automática precisa ser sobrescrita.
        """
        github_provider = get_repository_provider_explicit('github')
        assert isinstance(github_provider, GitHubRepositoryProvider)
        
        gitlab_provider = get_repository_provider_explicit('gitlab')
        assert isinstance(gitlab_provider, GitLabRepositoryProvider)
        
        azure_provider = get_repository_provider_explicit('azure')
        assert isinstance(azure_provider, AzureRepositoryProvider)
        
        # Testa alias para Azure
        azure_provider2 = get_repository_provider_explicit('azure_devops')
        assert isinstance(azure_provider2, AzureRepositoryProvider)
    
    def test_invalid_repository_names(self):
        """
        Testa tratamento de nomes de repositório inválidos.
        
        Nomes com menos de 2 partes ou vazios devem gerar ValueError.
        """
        invalid_names = [
            "",
            "   ",
            "single-part",
            "no-slash",
            None
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(ValueError):
                get_repository_provider(invalid_name)
    
    def test_invalid_explicit_provider_type(self):
        """
        Testa tratamento de tipos de provedor inválidos na criação explícita.
        """
        invalid_types = [
            "bitbucket",
            "svn",
            "unknown",
            "",
            "GITHUB"  # case sensitive test
        ]
        
        for invalid_type in invalid_types:
            with pytest.raises(ValueError):
                get_repository_provider_explicit(invalid_type)

class TestRepositoryReaderIntegration:
    """
    Testes de integração para leitura de repositórios com múltiplos provedores.
    
    Esta classe testa se o GitHubRepositoryReader funciona corretamente
    com diferentes provedores injetados via factory.
    """
    
    @patch('tools.github_reader.GitHubConnector')
    @patch('tools.github_reader.yaml.safe_load')
    @patch('builtins.open')
    def test_github_repository_reading(self, mock_open, mock_yaml, mock_connector):
        """
        Testa leitura de repositório GitHub com provider correto.
        
        Simula todo o fluxo de leitura usando mocks para evitar
        dependências externas nos testes.
        """
        # Setup dos mocks
        mock_yaml.return_value = {
            'refatoracao': {
                'extensions': ['.py', '.java']
            }
        }
        
        # Mock do repositório e suas respostas
        mock_repo = Mock()
        mock_repo.default_branch = 'main'
        
        # Mock da árvore Git
        mock_tree_element = Mock()
        mock_tree_element.type = 'blob'
        mock_tree_element.path = 'src/main.py'
        mock_tree_element.sha = 'abc123'
        
        mock_tree_response = Mock()
        mock_tree_response.tree = [mock_tree_element]
        mock_tree_response.truncated = False
        
        mock_repo.get_git_ref.return_value.object.sha = 'def456'
        mock_repo.get_git_tree.return_value = mock_tree_response
        
        # Mock do blob content
        mock_blob = Mock()
        mock_blob.content = 'cHJpbnQoImhlbGxvIHdvcmxkIik='  # base64 de 'print("hello world")'
        mock_repo.get_git_blob.return_value = mock_blob
        
        # Mock do connector
        mock_connector_instance = Mock()
        mock_connector_instance.connection.return_value = mock_repo
        mock_connector.return_value = mock_connector_instance
        
        # Teste da leitura
        github_provider = GitHubRepositoryProvider()
        reader = GitHubRepositoryReader(repository_provider=github_provider)
        
        resultado = reader.read_repository(
            nome_repo="microsoft/vscode",
            tipo_analise="refatoracao"
        )
        
        # Verificações
        assert isinstance(resultado, dict)
        assert 'src/main.py' in resultado
        assert resultado['src/main.py'] == 'print("hello world")'
        
        # Verifica se o connector foi chamado com o provider correto
        mock_connector.assert_called_once()
        call_args = mock_connector.call_args
        assert isinstance(call_args[1]['repository_provider'], GitHubRepositoryProvider)
    
    @patch('tools.github_reader.GitHubConnector')
    @patch('tools.github_reader.yaml.safe_load')
    @patch('builtins.open')
    def test_gitlab_repository_reading(self, mock_open, mock_yaml, mock_connector):
        """
        Testa leitura de repositório GitLab com provider correto.
        
        Verifica se a factory detecta corretamente GitLab e se o
        reader funciona com o provider injetado.
        """
        # Setup similar ao teste GitHub
        mock_yaml.return_value = {
            'analise': {
                'extensions': ['.js', '.ts']
            }
        }
        
        mock_repo = Mock()
        mock_repo.default_branch = 'master'
        
        mock_tree_element = Mock()
        mock_tree_element.type = 'blob'
        mock_tree_element.path = 'src/app.js'
        mock_tree_element.sha = 'xyz789'
        
        mock_tree_response = Mock()
        mock_tree_response.tree = [mock_tree_element]
        mock_tree_response.truncated = False
        
        mock_repo.get_git_ref.return_value.object.sha = 'uvw012'
        mock_repo.get_git_tree.return_value = mock_tree_response
        
        mock_blob = Mock()
        mock_blob.content = 'Y29uc29sZS5sb2coImhlbGxvIGZyb20gZ2l0bGFiIik='  # base64
        mock_repo.get_git_blob.return_value = mock_blob
        
        mock_connector_instance = Mock()
        mock_connector_instance.connection.return_value = mock_repo
        mock_connector.return_value = mock_connector_instance
        
        # Teste com repositório GitLab
        gitlab_provider = GitLabRepositoryProvider()
        reader = GitHubRepositoryReader(repository_provider=gitlab_provider)
        
        resultado = reader.read_repository(
            nome_repo="gitlab-org/gitlab",
            tipo_analise="analise"
        )
        
        # Verificações
        assert isinstance(resultado, dict)
        assert 'src/app.js' in resultado
        assert resultado['src/app.js'] == 'console.log("hello from gitlab")'
        
        # Verifica se o connector foi chamado com GitLab provider
        mock_connector.assert_called_once()
        call_args = mock_connector.call_args
        assert isinstance(call_args[1]['repository_provider'], GitLabRepositoryProvider)
    
    @patch('tools.github_reader.GitHubConnector')
    @patch('tools.github_reader.yaml.safe_load')
    @patch('builtins.open')
    def test_azure_devops_repository_reading(self, mock_open, mock_yaml, mock_connector):
        """
        Testa leitura de repositório Azure DevOps com provider correto.
        
        Verifica detecção de Azure DevOps (3 partes) e funcionamento
        do reader com o provider apropriado.
        """
        # Setup dos mocks
        mock_yaml.return_value = {
            'implementacao': {
                'extensions': ['.cs', '.csproj']
            }
        }
        
        mock_repo = Mock()
        mock_repo.default_branch = 'main'
        
        mock_tree_element = Mock()
        mock_tree_element.type = 'blob'
        mock_tree_element.path = 'Program.cs'
        mock_tree_element.sha = 'azure123'
        
        mock_tree_response = Mock()
        mock_tree_response.tree = [mock_tree_element]
        mock_tree_response.truncated = False
        
        mock_repo.get_git_ref.return_value.object.sha = 'azure456'
        mock_repo.get_git_tree.return_value = mock_tree_response
        
        mock_blob = Mock()
        mock_blob.content = 'dXNpbmcgU3lzdGVtOw=='  # base64 de 'using System;'
        mock_repo.get_git_blob.return_value = mock_blob
        
        mock_connector_instance = Mock()
        mock_connector_instance.connection.return_value = mock_repo
        mock_connector.return_value = mock_connector_instance
        
        # Teste com repositório Azure DevOps
        azure_provider = AzureRepositoryProvider()
        reader = GitHubRepositoryReader(repository_provider=azure_provider)
        
        resultado = reader.read_repository(
            nome_repo="myorg/myproject/myrepo",
            tipo_analise="implementacao"
        )
        
        # Verificações
        assert isinstance(resultado, dict)
        assert 'Program.cs' in resultado
        assert resultado['Program.cs'] == 'using System;'
        
        # Verifica se o connector foi chamado com Azure provider
        mock_connector.assert_called_once()
        call_args = mock_connector.call_args
        assert isinstance(call_args[1]['repository_provider'], AzureRepositoryProvider)
    
    def test_factory_integration_with_reader(self):
        """
        Testa integração completa da factory com o reader.
        
        Verifica se a detecção automática funciona corretamente
        quando integrada ao fluxo de leitura.
        """
        # Testa detecção automática para diferentes tipos
        test_cases = [
            ("microsoft/vscode", GitHubRepositoryProvider),
            ("gitlab-org/gitlab", GitLabRepositoryProvider),
            ("myorg/proj/repo", AzureRepositoryProvider)
        ]
        
        for repo_name, expected_provider_type in test_cases:
            provider = get_repository_provider(repo_name)
            assert isinstance(provider, expected_provider_type)
            
            # Verifica se o reader aceita o provider
            reader = GitHubRepositoryReader(repository_provider=provider)
            assert reader.repository_provider is provider
    
    def test_error_handling_in_factory(self):
        """
        Testa tratamento de erros na factory e sua propagação.
        
        Garante que erros são tratados graciosamente e com
        mensagens informativas.
        """
        # Teste com nome None
        with pytest.raises(ValueError, match="deve ser uma string não vazia"):
            get_repository_provider(None)
        
        # Teste com nome vazio
        with pytest.raises(ValueError, match="deve ser uma string não vazia"):
            get_repository_provider("")
        
        # Teste com formato inválido
        with pytest.raises(ValueError, match="formato inválido"):
            get_repository_provider("repo-sem-barra")
        
        # Teste com tipo explícito inválido
        with pytest.raises(ValueError, match="não reconhecido"):
            get_repository_provider_explicit("bitbucket")
    
    @patch('tools.repository_provider_factory.print')
    def test_logging_in_factory(self, mock_print):
        """
        Testa se a factory faz logging adequado das detecções.
        
        Verifica se mensagens informativas são geradas para
        debugging e monitoramento.
        """
        # Testa logging para cada tipo
        get_repository_provider("microsoft/vscode")
        mock_print.assert_called_with("Detectado repositório GitHub: microsoft/vscode")
        
        get_repository_provider("gitlab-org/gitlab")
        mock_print.assert_called_with("Detectado repositório GitLab: gitlab-org/gitlab")
        
        get_repository_provider("org/proj/repo")
        mock_print.assert_called_with("Detectado repositório Azure DevOps: org/proj/repo")