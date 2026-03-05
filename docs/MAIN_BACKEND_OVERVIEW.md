# Peers CodeAI Backend - main.py Overview

## Visão Geral

O arquivo `main.py` é o ponto de entrada do backend do projeto Peers CodeAI, implementado com FastAPI. Ele orquestra a inicialização da aplicação, configuração de logging estruturado, integração com Azure Key Vault, conexão com MongoDB, configuração de CORS, registro de routers de API e handlers de exceção.

## Funcionalidades Principais

### 1. Carregamento de Variáveis de Ambiente
- Utiliza `dotenv` para carregar variáveis do arquivo `.env`.

### 2. Configuração de Logging Estruturado
- Configuração global de logging com formatação JSON customizada (`JsonFormatter`).
- Logs incluem timestamp, nível, mensagem, função, módulo e campos extras.
- Stack trace de exceções é capturado e registrado.

### 3. Inicialização da Aplicação FastAPI
- Cria instância do FastAPI com título, descrição e versão.
- Configura middleware CORS para permitir origens, métodos e headers.

### 4. Registro de Routers
- Registra routers para diferentes domínios:
  - `/auth`: Autenticação
  - `/analysis`: Análise de código
  - `/session`: Gerenciamento de sessões
  - `/webhooks`: Integração via webhooks
  - `/user`: Projetos de usuário e agentes
  - `/projects`: Gerenciamento e ações de projetos
  - `/groups`: Grupos e permissões

### 5. Handlers de Exceção
- Handler para `StarletteHTTPException`: loga detalhes e retorna resposta JSON.
- Handler para exceções genéricas: loga stack trace e retorna erro 500.

### 6. Evento de Startup
- Carrega segredos do Azure Key Vault via `ConfigLoaderService`.
- Inicializa serviço MongoDB (`MongoDBService`), armazena na aplicação e cria índices.
- Loga status de inicialização.

## Fluxo de Inicialização (Mermaid)

mermaid
flowchart TD
    A[Início main.py] --> B[Carrega .env]
    B --> C[Configura Logging JSON]
    C --> D[Cria FastAPI]
    D --> E[Configura CORS]
    E --> F[Registra Routers]
    F --> G[Evento Startup]
    G --> H[Carrega segredos Key Vault]
    H --> I[Inicializa MongoDBService]
    I --> J[Cria índices MongoDB]
    J --> K[Aplicação pronta]


## Estrutura de Pastas e Arquivos

### Árvore de Diretórios (simplificada)


backend/
  app/
    api/
      analysis.py
      auth.py
      ...
    core/
      config.py
    models/
      group_models.py
      ...
    services/
      mongodb_service.py
      ...
    utils/
      logging_utils.py
      ...
  config/
    agent_mapping.py
    ...
docs/
main.py
requirements.txt
startup.py


### Análise do Design de Estrutura

- **Separação de Responsabilidades:**
  - `api/`: Endpoints da API, cada domínio em um arquivo.
  - `models/`: Modelos de dados (Pydantic, MongoDB).
  - `services/`: Lógica de negócio e integração com recursos externos (MongoDB, Azure, Redis).
  - `utils/`: Utilitários e funções auxiliares.
  - `core/`: Configurações centrais.
  - `config/`: Arquivos de configuração e mapeamento de agentes.

- **Pontos Fortes:**
  - Estrutura modular, facilita manutenção e evolução.
  - Separação clara entre API, modelos e serviços.
  - Uso de FastAPI, Pydantic, logging estruturado.
  - Integração com Azure e MongoDB.

- **Pontos de Atenção:**
  - Possível acoplamento entre arquivos de projeto (`project_actions.py` e `project_management.py`).
  - Falta de camada de repositório para abstrair acesso ao MongoDB.
  - Ausência de testes na estrutura visível.
  - Configurações de agentes poderiam ser melhor organizadas.

- **Recomendações de Melhoria:**
  - Criar pasta `backend/app/repositories/` para isolar lógica de acesso a dados.
  - Adicionar pasta `backend/tests/` com estrutura espelhada para testes.
  - Separar configurações de agentes MCP em `backend/app/config/agents/`.
  - Considerar criação de `backend/app/middleware/` para middlewares customizados.
  - Documentar dependências críticas em `docs/DEPENDENCIES.md`.

## Conclusão

A estrutura atual é adequada para projetos FastAPI de médio porte, com boa separação de responsabilidades. Para maior escalabilidade e manutenção, recomenda-se introduzir camadas de repositório, testes automatizados e organização mais granular das configurações e middlewares.
