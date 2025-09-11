# Wiki - Multi-Agent Code Platform (MCP)

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura Geral do Projeto](#estrutura-geral-do-projeto)
3. [Descrição das Pastas](#descrição-das-pastas)
4. [Como Adicionar uma Nova API de LLM](#como-adicionar-uma-nova-api-de-llm)
5. [Como Adicionar um Novo Repositório](#como-adicionar-um-novo-repositório)
6. [Fluxo de Execução](#fluxo-de-execução)
7. [Configuração e Deploy](#configuração-e-deploy)

---

## 🎯 Visão Geral

O **Multi-Agent Code Platform (MCP)** é uma plataforma robusta que orquestra agentes de IA para análise e refatoração de código em repositórios GitHub, GitLab e Azure DevOps. A arquitetura segue princípios de **Clean Architecture** com injeção de dependências, garantindo alta modularidade e testabilidade.

### Principais Características:
- ✅ Suporte a múltiplos provedores de repositório (GitHub, GitLab, Azure DevOps)
- ✅ Integração com múltiplos provedores de LLM (OpenAI, Claude)
- ✅ Sistema de workflows configuráveis via YAML
- ✅ Armazenamento de jobs com Redis
- ✅ Sistema de aprovação para mudanças críticas
- ✅ Upload automático de relatórios para Azure Blob Storage
- ✅ Sistema RAG para políticas empresariais
- ✅ API REST completa com FastAPI

---

## 🏗️ Estrutura Geral do Projeto


mcp-server/
├── agents/                     # Agentes de IA especializados
├── domain/                     # Camada de domínio (interfaces)
├── services/                   # Camada de serviços e orquestração
├── tools/                      # Ferramentas e utilitários
├── docs/                       # Documentação
├── workflows.yaml              # Configuração de workflows
├── mcp_server_fastapi.py       # Servidor principal FastAPI
└── requirements.txt            # Dependências Python


---

## 📁 Descrição das Pastas

### 🤖 `/agents`
Contém os agentes de IA especializados que executam tarefas específicas.

- **`agente_revisor.py`**: Agente responsável por análise de código em repositórios
- **`agente_processador.py`**: Agente que processa resultados de outras etapas
- **`logging_utils.py`**: Utilitários para logging com Azure Application Insights

### 🏛️ `/domain/interfaces`
Camada de domínio seguindo Clean Architecture - define contratos através de interfaces.

- **`llm_provider_interface.py`**: Interface para provedores de LLM
- **`repository_reader_interface.py`**: Interface para leitores de repositório
- **`repository_provider_interface.py`**: Interface para provedores de repositório
- **`secret_manager_interface.py`**: Interface para gerenciamento de segredos
- **`job_manager_interface.py`**: Interface para gerenciamento de jobs
- **`blob_storage_interface.py`**: Interface para armazenamento de blobs
- **`workflow_orchestrator_interface.py`**: Interface para orquestração de workflows
- **`rag_retriever_interface.py`**: Interface para sistema RAG
- **`changeset_filler_interface.py`**: Interface para preenchimento de changesets
- **`job_store_interface.py`**: Interface para armazenamento de jobs

### ⚙️ `/services`
Camada de serviços que implementa a lógica de negócio.

- **`workflow_orchestrator.py`**: Orquestrador principal de workflows
- **`job_manager.py`**: Gerenciador de jobs e estados
- **`blob_storage_service.py`**: Serviço para Azure Blob Storage
- **`factories/`**: Fábricas para criação de objetos
  - **`agent_factory.py`**: Fábrica de agentes
  - **`llm_provider_factory.py`**: Fábrica de provedores LLM

### 🔧 `/tools`
Ferramentas e utilitários especializados.

#### Conectores (`/tools/conectores`)
- **`conexao_geral.py`**: Orquestrador geral de conexões
- **`base_conector.py`**: Classe base para conectores
- **`github_conector.py`**: Conector específico para GitHub
- **`gitlab_conector.py`**: Conector específico para GitLab
- **`azure_conector.py`**: Conector específico para Azure DevOps

#### Leitores (`/tools/readers`)
- **`reader_geral.py`**: Leitor geral que delega para leitores específicos
- **`base_reader.py`**: Classe base para leitores
- **`github_reader.py`**: Leitor específico para GitHub
- **`gitlab_reader.py`**: Leitor específico para GitLab
- **`azure_reader.py`**: Leitor específico para Azure DevOps

#### Committers (`/tools/repo_committers`)
- **`orchestrator.py`**: Orquestrador de commits por provedor
- **`base_committer.py`**: Classe base para committers
- **`github_committer.py`**: Committer específico para GitHub
- **`gitlab_committer.py`**: Committer específico para GitLab
- **`azure_committer.py`**: Committer específico para Azure DevOps

#### Outros Utilitários
- **`requisicao_openai.py`**: Provedor OpenAI/Azure OpenAI
- **`requisicao_claude.py`**: Provedor Anthropic Claude
- **`rag_retriever.py`**: Sistema RAG com Azure AI Search
- **`preenchimento.py`**: Preenchimento de changesets
- **`job_store.py`**: Armazenamento Redis para jobs
- **`azure_secret_manager.py`**: Gerenciador de segredos Azure Key Vault
- **`blob_report_*.py`**: Utilitários para Azure Blob Storage

---

## 🚀 Como Adicionar uma Nova API de LLM

### Passo 1: Criar o Provedor

Crie um novo arquivo em `/tools/` (ex: `requisicao_gemini.py`):

python
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from domain.interfaces.rag_retriever_interface import IRAGRetriever
from domain.interfaces.secret_manager_interface import ISecretManager
from tools.azure_secret_manager import AzureSecretManager

class GeminiLLMProvider(ILLMProviderComplete):
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None, secret_manager: ISecretManager = None):
        self.rag_retriever = rag_retriever
        self.secret_manager = secret_manager or AzureSecretManager()
        
        # Configurar cliente da API
        api_key = self.secret_manager.get_secret("GEMINI_API_KEY")
        # ... inicialização do cliente
    
    def carregar_prompt(self, tipo_tarefa: str) -> str:
        # Implementar carregamento de prompts
        pass
    
    def executar_prompt(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # Implementar lógica de execução
        # Deve retornar: {'reposta_final': str, 'tokens_entrada': int, 'tokens_saida': int}
        pass
    
    # Implementar outros métodos da interface...


### Passo 2: Registrar na Factory

Edite `/services/factories/llm_provider_factory.py`:

python
from tools.requisicao_gemini import GeminiLLMProvider  # Adicionar import

class LLMProviderFactory:
    _providers: Dict[str, Type[ILLMProvider]] = {
        'openai': OpenAILLMProvider,
        'claude': AnthropicClaudeProvider,
        'gemini': GeminiLLMProvider,  # Adicionar aqui
    }
    
    @classmethod
    def create_provider(cls, model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
        model_lower = (model_name or "").lower()
        
        if "gemini" in model_lower:  # Adicionar detecção
            provider_class = cls._providers.get('gemini', OpenAILLMProvider)
        elif "claude" in model_lower:
            provider_class = cls._providers.get('claude', OpenAILLMProvider)
        else:
            provider_class = cls._providers.get('openai', OpenAILLMProvider)
        
        return provider_class(rag_retriever=rag_retriever)


### Passo 3: Configurar Segredos

Adicione as chaves necessárias no Azure Key Vault:
- `GEMINI_API_KEY`: Chave da API do Gemini

### Passo 4: Atualizar Requirements

Adicione as dependências necessárias no `requirements.txt`:

google-generativeai==0.3.2


---

## 📦 Como Adicionar um Novo Repositório

### Passo 1: Criar o Repository Provider

Crie um novo arquivo em `/tools/` (ex: `bitbucket_repository_provider.py`):

python
from typing import Any
from domain.interfaces.repository_provider_interface import IRepositoryProvider

class BitbucketRepositoryProvider(IRepositoryProvider):
    def get_repository(self, repository_name: str, token: str) -> Any:
        # Implementar lógica para obter repositório
        pass
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Any:
        # Implementar lógica para criar repositório
        pass


### Passo 2: Criar o Conector

Crie `/tools/conectores/bitbucket_conector.py`:

python
from tools.conectores.base_conector import BaseConector
from tools.bitbucket_repository_provider import BitbucketRepositoryProvider

class BitbucketConector(BaseConector):
    def _extract_org_name(self, repositorio: str) -> str:
        # Implementar extração do nome da organização
        pass
    
    def connection(self, repositorio: str):
        org_name = self._extract_org_name(repositorio)
        return self._handle_repository_connection(repositorio, "Bitbucket", org_name)
    
    @classmethod
    def create_with_defaults(cls) -> 'BitbucketConector':
        return cls(repository_provider=BitbucketRepositoryProvider())


### Passo 3: Criar o Reader

Crie `/tools/readers/bitbucket_reader.py`:

python
from typing import Dict, Optional, List
from tools.readers.base_reader import BaseReader
from tools.bitbucket_repository_provider import BitbucketRepositoryProvider

class BitbucketReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or BitbucketRepositoryProvider())
    
    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        # Implementar lógica de leitura
        pass


### Passo 4: Criar o Committer

Crie `/tools/repo_committers/bitbucket_committer.py`:

python
from typing import Dict, Any
from tools.repo_committers.base_committer import BaseCommitter

def processar_branch_bitbucket(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    # Implementar lógica de commit e PR
    pass


### Passo 5: Integrar no Sistema

#### 5.1 Atualizar ConexaoGeral

Edite `/tools/conectores/conexao_geral.py`:

python
from tools.conectores.bitbucket_conector import BitbucketConector  # Adicionar import

class ConexaoGeral:
    def _get_conector(self, repository_type: str, repository_provider: IRepositoryProvider):
        # ... código existente ...
        elif repository_type == 'bitbucket':  # Adicionar
            conector = BitbucketConector(repository_provider, self.secret_manager)
        # ... resto do código ...


#### 5.2 Atualizar ReaderGeral

Edite `/tools/readers/reader_geral.py`:

python
from .bitbucket_reader import BitbucketReader  # Adicionar import

class ReaderGeral(IRepositoryReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        # ... código existente ...
        self.bitbucket_reader = BitbucketReader(repository_provider)  # Adicionar
    
    def read_repository(self, ...):
        # ... código existente ...
        elif repository_type == 'bitbucket':  # Adicionar
            resultado = self.bitbucket_reader.read_repository_internal(...)
        # ... resto do código ...


#### 5.3 Atualizar Orchestrator

Edite `/tools/repo_committers/orchestrator.py`:

python
from .bitbucket_committer import processar_branch_bitbucket  # Adicionar import

def processar_branch_por_provedor(...):
    if repository_type == 'bitbucket':  # Adicionar
        return processar_branch_bitbucket(...)
    # ... resto do código ...


#### 5.4 Atualizar Factory

Edite `/tools/repository_provider_factory.py`:

python
from tools.bitbucket_repository_provider import BitbucketRepositoryProvider  # Adicionar

def get_repository_provider_explicit(provider_type: str) -> IRepositoryProvider:
    # ... código existente ...
    elif provider_type == 'bitbucket':  # Adicionar
        return BitbucketRepositoryProvider()
    # ... resto do código ...


#### 5.5 Atualizar API

Edite `mcp_server_fastapi.py` para adicionar 'bitbucket' como opção válida:

python
repository_type: Literal['github', 'gitlab', 'azure', 'bitbucket'] = Field(...)


### Passo 6: Configurar Segredos

Adicione no Azure Key Vault:
- `bitbucket-token`: Token padrão
- `bitbucket-token-{org}`: Tokens específicos por organização

---

## 🔄 Fluxo de Execução

### 1. Recepção da Requisição
- FastAPI recebe requisição em `/start-analysis`
- Valida parâmetros e cria job no Redis
- Inicia workflow em background

### 2. Orquestração do Workflow
- `WorkflowOrchestrator` carrega configuração do `workflows.yaml`
- Executa etapas sequencialmente
- Gerencia estados e aprovações

### 3. Execução dos Agentes
- `AgentFactory` cria agentes especializados
- `LLMProviderFactory` fornece provedor de IA apropriado
- Agentes processam código e geram resultados

### 4. Processamento de Resultados
- `ChangesetFiller` preenche detalhes dos changesets
- Sistema valida e agrupa mudanças por branch

### 5. Commit e PR
- Conectores específicos criam branches
- Committers aplicam mudanças
- Sistema cria Pull/Merge Requests

---

## ⚙️ Configuração e Deploy

### Variáveis de Ambiente Obrigatórias

bash
# Redis
REDIS_URL=redis://...

# Azure Key Vault
KEY_VAULT_URL=https://your-vault.vault.azure.net/

# Azure OpenAI
AZURE_OPENAI_MODELS=https://your-openai.openai.azure.com/
AZURE_DEFAULT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_MODEL_NAME=text-embedding-ada-002

# Azure AI Search (RAG)
AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
AI_SEARCH_INDEX_NAME=your-index

# Azure Blob Storage
AZURE_STORAGE_CONTAINER_NAME=reports
AZURE_STORAGE_CONNECTION_STRING=azure-storage-connection

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...


### Segredos no Azure Key Vault


# LLM APIs
openaiapi
ANTHROPICAAPIKEY

# Repository Tokens
github-token
gitlab-token
azure-token

# Azure Services
azure-openai-modelos
aisearchapi
azure-storage-connection


### Deploy

1. **Instalar dependências**:
   bash
   pip install -r requirements.txt
   

2. **Configurar variáveis de ambiente**

3. **Executar servidor**:
   bash
   uvicorn mcp_server_fastapi:app --host 0.0.0.0 --port 8000
   

---

## 📚 Recursos Adicionais

- **Logs**: Sistema integrado com Azure Application Insights
- **Monitoramento**: Métricas de tokens, tempo de execução e erros
- **Cache**: Sistema de cache para repositórios e conexões
- **Retry**: Lógica de retry automática para APIs externas
- **Validação**: Validação robusta de entrada com Pydantic

---

*Esta wiki é mantida pela equipe de desenvolvimento. Para contribuições ou dúvidas, abra uma issue no repositório.*