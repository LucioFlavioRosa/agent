# MCP Server - Multi-Agent Code Platform

## Wiki de Documentação Técnica

---

## 1. Estrutura Geral do Projeto

O **MCP Server** é uma plataforma robusta para orquestração de agentes de IA que automatiza análises de código e geração de implementações. O sistema utiliza uma arquitetura baseada em microserviços com FastAPI, Redis para persistência de jobs e Azure Blob Storage para armazenamento de relatórios.

### Arquitetura Principal


MCP Server
├── API Layer (FastAPI)
├── Workflow Orchestrator
├── Job Manager
├── Storage Services (Redis + Blob)
└── Tools & Services


### Fluxo de Execução

1. **Recepção de Requisição**: API recebe solicitação de análise
2. **Criação de Job**: Sistema gera job único com UUID
3. **Orquestração**: Workflow Orchestrator executa etapas definidas
4. **Processamento**: Agentes de IA processam código conforme workflow
5. **Armazenamento**: Resultados são persistidos no Redis e Blob Storage
6. **Resposta**: API retorna status e resultados ao cliente

---

## 2. Descrição de Cada Pasta

### `/docs/`
**Propósito**: Documentação técnica e guias do projeto
- Contém esta wiki e outros documentos de referência
- Manuais de instalação e configuração
- Exemplos de uso e casos de teste

### `/services/`
**Propósito**: Serviços principais da aplicação
- `workflow_orchestrator.py`: Coordena execução de workflows
- `job_manager.py`: Gerencia ciclo de vida dos jobs
- `blob_storage_service.py`: Interface com Azure Blob Storage
- Outros serviços especializados

### `/tools/`
**Propósito**: Ferramentas e utilitários
- `job_store.py`: Abstração para persistência Redis
- Utilitários de validação e formatação
- Helpers para integração com APIs externas

### `/workflows/`
**Propósito**: Definições de workflows em YAML
- `workflows.yaml`: Configurações de todos os workflows disponíveis
- Templates de análise por tipo de projeto
- Configurações de etapas e dependências

### `/config/`
**Propósito**: Arquivos de configuração
- Configurações de ambiente
- Credenciais e chaves de API
- Parâmetros de conexão com serviços externos

### `/tests/`
**Propósito**: Testes automatizados
- Testes unitários dos serviços
- Testes de integração da API
- Mocks e fixtures para desenvolvimento

---

## 3. Como Adicionar uma Nova API de LLM

### Passo 1: Criar o Serviço de LLM

Crie um novo arquivo em `/services/llm_providers/`:

python
# services/llm_providers/nova_api_llm.py
from typing import Dict, Any, Optional
from .base_llm_provider import BaseLLMProvider

class NovaAPILLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
    
    async def generate_response(self, prompt: str, model: str = "default") -> str:
        # Implementar lógica de chamada para a nova API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": 4000
        }
        
        # Fazer requisição HTTP para a API
        # Processar resposta
        # Retornar texto gerado
        pass
    
    def get_available_models(self) -> list:
        return ["modelo-1", "modelo-2", "modelo-premium"]


### Passo 2: Registrar no Factory Pattern

Edite `/services/llm_factory.py`:

python
from .llm_providers.nova_api_llm import NovaAPILLMProvider

class LLMFactory:
    @staticmethod
    def create_provider(provider_type: str, **kwargs):
        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "nova_api": NovaAPILLMProvider,  # Adicionar aqui
        }
        
        if provider_type not in providers:
            raise ValueError(f"Provider {provider_type} não suportado")
        
        return providers[provider_type](**kwargs)


### Passo 3: Configurar Variáveis de Ambiente

Adicione no arquivo `.env`:

env
NOVA_API_KEY=sua_chave_aqui
NOVA_API_BASE_URL=https://api.nova-llm.com/v1


### Passo 4: Atualizar Workflows

Edite `workflows.yaml` para incluir a nova opção:

yaml
analise_codigo:
  steps:
    - name: "analise_inicial"
      agent: "code_analyzer"
      llm_providers:
        - "openai"
        - "anthropic"
        - "nova_api"  # Adicionar aqui
      default_model: "gpt-4"
      nova_api_model: "modelo-premium"  # Modelo específico


### Passo 5: Testes

Crie testes em `/tests/test_nova_api_llm.py`:

python
import pytest
from services.llm_providers.nova_api_llm import NovaAPILLMProvider

@pytest.fixture
def nova_provider():
    return NovaAPILLMProvider(
        api_key="test_key",
        base_url="https://test.api.com"
    )

def test_generate_response(nova_provider):
    # Implementar testes unitários
    pass


---

## 4. Como Adicionar um Novo Repositório

### Passo 1: Criar o Connector

Crie um novo arquivo em `/services/repository_connectors/`:

python
# services/repository_connectors/novo_repo_connector.py
from typing import Dict, List, Optional
from .base_repository_connector import BaseRepositoryConnector

class NovoRepoConnector(BaseRepositoryConnector):
    def __init__(self, access_token: str, base_url: str):
        self.access_token = access_token
        self.base_url = base_url
    
    async def clone_repository(self, repo_name: str, branch: str = "main") -> str:
        # Implementar lógica de clone
        # Retornar caminho local do repositório clonado
        pass
    
    async def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> bool:
        # Implementar criação de branch
        pass
    
    async def create_pull_request(self, repo_name: str, source_branch: str, target_branch: str, title: str, description: str) -> str:
        # Implementar criação de PR
        # Retornar URL do PR criado
        pass
    
    async def commit_changes(self, repo_path: str, message: str, files: List[str]) -> str:
        # Implementar commit de mudanças
        # Retornar hash do commit
        pass
    
    def validate_repo_name(self, repo_name: str) -> str:
        # Implementar validação específica do formato
        # Exemplo: para Bitbucket pode ser "workspace/repo-name"
        if "/" not in repo_name:
            raise ValueError("Formato inválido. Use: workspace/repo-name")
        return repo_name


### Passo 2: Registrar no Factory

Edite `/services/repository_factory.py`:

python
from .repository_connectors.novo_repo_connector import NovoRepoConnector

class RepositoryFactory:
    @staticmethod
    def create_connector(repo_type: str, **kwargs):
        connectors = {
            "github": GitHubConnector,
            "gitlab": GitLabConnector,
            "azure": AzureDevOpsConnector,
            "novo_repo": NovoRepoConnector,  # Adicionar aqui
        }
        
        if repo_type not in connectors:
            raise ValueError(f"Tipo de repositório {repo_type} não suportado")
        
        return connectors[repo_type](**kwargs)


### Passo 3: Atualizar Modelos Pydantic

Edite `mcp_server_fastapi.py`:

python
class StartAnalysisPayload(BaseModel):
    # ... outros campos ...
    repository_type: Literal['github', 'gitlab', 'azure', 'novo_repo'] = Field(
        description="Tipo do repositório: 'github', 'gitlab', 'azure', 'novo_repo'."
    )


### Passo 4: Implementar Validação Específica

Adicione função de validação em `mcp_server_fastapi.py`:

python
def _validate_and_normalize_novo_repo_name(repo_name: str) -> str:
    repo_name = repo_name.strip()
    
    if '/' not in repo_name:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de repositório NovoRepo inválido: '{repo_name}'. Use o formato 'workspace/repo-name'."
        )
    
    parts = repo_name.split('/')
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido. Esperado exatamente 'workspace/repo-name', recebido: '{repo_name}'"
        )
    
    return repo_name

def _normalize_repo_name_by_type(repo_name: str, repository_type: str) -> str:
    """Normaliza o nome do repositório baseado no tipo."""
    if repository_type == 'gitlab':
        return _validate_and_normalize_gitlab_repo_name(repo_name)
    elif repository_type == 'novo_repo':
        return _validate_and_normalize_novo_repo_name(repo_name)
    return repo_name


### Passo 5: Configurar Credenciais

Adicione no arquivo `.env`:

env
NOVO_REPO_ACCESS_TOKEN=seu_token_aqui
NOVO_REPO_BASE_URL=https://api.novo-repo.com/v2


### Passo 6: Atualizar Documentação da API

A documentação Swagger será automaticamente atualizada com o novo tipo de repositório devido ao uso de `Literal` no Pydantic.

### Passo 7: Testes de Integração

Crie testes em `/tests/test_novo_repo_integration.py`:

python
import pytest
from services.repository_connectors.novo_repo_connector import NovoRepoConnector

@pytest.fixture
def novo_repo_connector():
    return NovoRepoConnector(
        access_token="test_token",
        base_url="https://test.novo-repo.com"
    )

def test_validate_repo_name(novo_repo_connector):
    # Testar validação de nomes
    valid_name = "workspace/my-repo"
    assert novo_repo_connector.validate_repo_name(valid_name) == valid_name
    
    with pytest.raises(ValueError):
        novo_repo_connector.validate_repo_name("invalid-format")


---

## Considerações Importantes

### Segurança
- Sempre use variáveis de ambiente para credenciais
- Implemente rate limiting para APIs externas
- Valide e sanitize todas as entradas de usuário

### Performance
- Use conexões assíncronas quando possível
- Implemente cache para operações repetitivas
- Configure timeouts apropriados para APIs externas

### Monitoramento
- Adicione logs estruturados para debugging
- Implemente métricas de performance
- Configure alertas para falhas críticas

### Manutenibilidade
- Siga os padrões de código existentes
- Documente todas as funções públicas
- Mantenha testes atualizados

---

## Recursos Adicionais

- **Swagger UI**: Disponível em `/docs` quando o servidor estiver rodando
- **Logs**: Configurados para output estruturado em JSON
- **Health Check**: Endpoint `/health` para monitoramento
- **Métricas**: Endpoint `/metrics` para Prometheus

---

*Última atualização: $(date)*
*Versão da API: 9.0.0*