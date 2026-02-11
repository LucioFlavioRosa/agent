# Startup e Configuração da Solução

Este documento descreve o fluxo de inicialização da aplicação, detalhando a ordem de carregamento de configurações, segredos, validação de variáveis de ambiente, inicialização de serviços e middlewares aplicados.

## 1. Ordem de Inicialização

A aplicação é inicializada a partir dos arquivos `startup.py` e `main.py`. O fluxo é:

1. **Carregamento de variáveis de ambiente**: Utiliza o pacote `dotenv` para carregar variáveis do arquivo `.env`.
2. **Validação de variáveis obrigatórias**: Antes de iniciar serviços, valida-se a presença de variáveis essenciais (como conexões Azure e MongoDB).
3. **Carregamento de segredos do Azure Key Vault**: Segredos sensíveis (ex: Redis) são buscados do Key Vault via `ConfigLoaderService`.
4. **Inicialização de serviços**:
   - **MongoDB**: Instanciado globalmente com URI e nome do banco.
   - **Redis**: Instanciado com segredos carregados.
5. **Configuração de middlewares**:
   - **Restrição de IP**: Middleware que limita acesso a IPs autorizados.
   - **CORS**: Permite requisições de qualquer origem.
6. **Registro de rotas**: Cada módulo de API é registrado no FastAPI.
7. **Setup de logging**: Logging estruturado em JSON.

## 2. Variáveis de Ambiente Obrigatórias

- `AZURE_STORAGE_CONNECTION_STRING`: Conexão com Azure Blob Storage
- `AZURE_STORAGE_CONTAINER_NAME`: Nome do container Azure Blob
- `MONGODB_URI`: URI de conexão com MongoDB
- `MONGODB_DATABASE_NAME`: Nome do banco MongoDB
- `ALLOWED_IPS`: Lista de IPs permitidos (opcional)
- `LOG_LEVEL`: Nível de logging (opcional)

## 3. Segredos Buscados no Key Vault

Os seguintes segredos são buscados do Azure Key Vault:

- `redis-host`: Host do Redis
- `redis-port`: Porta do Redis
- `redis-password`: Senha do Redis
- `redis-db`: Número do banco Redis
- `redis-use-ssl`: Flag de uso de SSL
- `redis-ssl-cert-reqs`: Requisição de certificado SSL

Caso algum segredo não seja encontrado no Key Vault, o sistema faz fallback para variáveis de ambiente ou valores default.

## 4. Inicialização de Serviços

- **MongoDBService**: Instanciado globalmente na aplicação, utilizando URI e nome do banco.
- **RedisSessionService**: Instanciado com segredos carregados.

## 5. Middlewares Aplicados

- **IP Restriction Middleware**: Bloqueia requisições de IPs não autorizados, exceto para rotas de documentação.
- **CORS Middleware**: Permite requisições de qualquer origem, credenciais, métodos e headers.

## 6. Rotas Registradas

As rotas são registradas conforme os routers importados em `main.py`:

- `/auth`: Autenticação
- `/analysis`: Análise multiagente
- `/projects`: Operações de projetos (verificação, listagem, gerenciamento)
- `/session`: Sessão e relatórios
- `/webhooks`: Webhooks do MCP
- `/user`: Projetos do usuário

Cada rota possui documentação específica (ver documentos por rota).

## 7. Observações

- O fluxo de startup garante que todos os segredos e variáveis obrigatórias estejam presentes antes de iniciar endpoints.
- Em caso de falha no carregamento de segredos, o sistema pode iniciar em modo degradado, utilizando apenas variáveis locais.
