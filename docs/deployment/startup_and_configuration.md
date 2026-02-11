# Documentação de Startup e Configuração

Este documento descreve o processo de inicialização da aplicação, carregamento de configurações, segredos, validação de variáveis de ambiente obrigatórias, inicialização de serviços e middlewares aplicados.

---

## 1. Ordem de Inicialização

A inicialização ocorre em duas etapas principais:

- **startup.py**: Carrega variáveis de ambiente do arquivo `.env`, valida variáveis obrigatórias, e executa o carregamento de segredos sensíveis do Azure Key Vault.
- **main.py**: Inicializa o FastAPI, configura middlewares, valida variáveis de ambiente, inicializa serviços MongoDB e Redis, e carrega segredos via `ConfigLoaderService`.

---

## 2. Carregamento de Configurações

- **Variáveis de ambiente** são carregadas do arquivo `.env` na raiz do backend.
- **Segredos sensíveis** (como credenciais do Redis) são buscados no Azure Key Vault através do serviço `ConfigLoaderService`.
- Caso algum segredo não seja encontrado no Key Vault, o sistema faz fallback para variáveis de ambiente ou valores definidos em `settings`.

### Variáveis de Ambiente Obrigatórias

- `AZURE_STORAGE_CONNECTION_STRING`: String de conexão com Azure Blob Storage.
- `AZURE_STORAGE_CONTAINER_NAME`: Nome do container do Azure Blob Storage.
- `MONGODB_URI`: URI de conexão com MongoDB.
- `MONGODB_DATABASE_NAME`: Nome do banco de dados MongoDB.
- `ALLOWED_IPS`: Lista de IPs permitidos para acesso à API (opcional).
- `LOG_LEVEL`: Nível de logging (opcional).

### Segredos Buscados no Azure Key Vault

Os seguintes segredos são buscados no Key Vault (cofre):

- `redis-host`: Host do Redis
- `redis-port`: Porta do Redis
- `redis-password`: Senha do Redis
- `redis-db`: Número do banco Redis
- `redis-use-ssl`: Uso de SSL no Redis
- `redis-ssl-cert-reqs`: Requisições de certificado SSL

Caso não estejam presentes no Key Vault, o sistema busca nas variáveis de ambiente correspondentes.

---

## 3. Inicialização de Serviços

- **MongoDBService**: Inicializado globalmente com URI e nome do banco obtidos das variáveis de ambiente ou settings.
- **RedisSessionService**: Inicializado com segredos carregados do Key Vault ou variáveis de ambiente.

---

## 4. Middlewares Aplicados

- **IP Restriction Middleware**: Restringe acesso à API apenas aos IPs definidos em `ALLOWED_IPS`. Permite acesso livre à documentação (`/docs`, `/openapi.json`, `/redoc`).
- **CORS Middleware**: Permite requisições de qualquer origem, métodos e headers.

---

## 5. Rotas da Solução

A aplicação expõe as seguintes rotas, cada uma documentada separadamente:

- `/auth`: Autenticação
- `/analysis`: Análise multiagente
- `/projects`: Operações de projetos (verificação, listagem, gerenciamento de membros)
- `/session`: Sessão e relatórios
- `/webhooks`: Webhooks (integração com MCP)
- `/user`: Projetos do usuário

Consulte a documentação de cada rota para detalhes sobre endpoints, parâmetros e respostas.

---

## 6. Fluxo de Startup

1. Carregamento das variáveis de ambiente do `.env`.
2. Validação das variáveis obrigatórias.
3. Carregamento de segredos do Key Vault.
4. Inicialização dos serviços MongoDB e Redis.
5. Configuração dos middlewares.
6. Registro das rotas FastAPI.

---

## 7. Observações

- Caso falte alguma variável obrigatória ou segredo, o sistema pode iniciar em modo degradado, usando apenas variáveis locais.
- Todos os logs de inicialização e erros são registrados com nível configurável.

