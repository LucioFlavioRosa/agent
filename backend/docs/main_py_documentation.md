# Documentação Detalhada: backend/app/main.py

## Índice
- [Visão Geral](#visão-geral)
- [Importações e Dependências](#importações-e-dependências)
- [Configuração da Aplicação FastAPI](#configuração-da-aplicação-fastapi)
- [Middleware CORS](#middleware-cors)
- [Middleware de Autenticação JWT](#middleware-de-autenticação-jwt)
- [Registro de Routers](#registro-de-routers)
- [Tratadores de Exceções Globais](#tratadores-de-exceções-globais)
- [Fluxo de Requisição (Texto)](#fluxo-de-requisição-texto)
- [Fluxo de Requisição (Diagrama Mermaid)](#fluxo-de-requisição-diagrama-mermaid)
- [Exemplos Práticos](#exemplos-práticos)
- [Arquitetura de Componentes (Mermaid)](#arquitetura-de-componentes-mermaid)
- [Considerações de Segurança e Boas Práticas](#considerações-de-segurança-e-boas-práticas)

---

## Visão Geral

O arquivo `main.py` é o ponto de entrada da aplicação backend desenvolvida com FastAPI. Ele configura middlewares essenciais, registra routers de autenticação e upload, e define tratadores globais de exceções para garantir robustez e segurança na API.

---

## Importações e Dependências

- **FastAPI**: Framework principal para construção da API.
- **Request, HTTPException**: Manipulação de requisições e exceções HTTP.
- **JSONResponse**: Resposta customizada em JSON.
- **CORSMiddleware**: Middleware para controle de CORS.
- **BaseHTTPMiddleware**: Base para criação de middlewares customizados.
- **Status HTTP**: Códigos de status HTTP padrão.
- **Routers**: `auth_router` e `upload_router` para modularização dos endpoints.
- **AuthMiddleware**: Middleware customizado para validação de JWT.

---

## Configuração da Aplicação FastAPI

A aplicação é instanciada com título, descrição e versão. Isso facilita a documentação automática e a identificação da API.

python
app = FastAPI(title="Backend API", description="Backend para upload e autenticação JWT", version="1.0.0")


---

## Middleware CORS

O CORS (Cross-Origin Resource Sharing) é configurado para permitir requisições de qualquer origem (`allow_origins=["*"]`). Isso é útil para ambientes de desenvolvimento, mas recomenda-se restringir em produção.

python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


- **Propósito**: Permitir que o frontend (mesmo hospedado em outro domínio) acesse a API sem bloqueios do navegador.
- **Configuração**: Permissiva para facilitar integração, mas deve ser revisada para produção.

---

## Middleware de Autenticação JWT

O `AuthMiddleware` é adicionado para interceptar todas as requisições e validar o token JWT.

python
app.add_middleware(AuthMiddleware)


- **Fluxo**: Antes de qualquer endpoint ser acessado, o middleware verifica a presença e validade do JWT no header Authorization.
- **Falha**: Se o token for inválido ou ausente, retorna HTTP 401.

---

## Registro de Routers

Os routers são responsáveis por agrupar endpoints relacionados:

python
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/upload", tags=["upload"])


- **auth_router**: Endpoints de autenticação (login, registro, etc).
- **upload_router**: Endpoints para upload de arquivos.

---

## Tratadores de Exceções Globais

Três tratadores são definidos para capturar e responder a erros de forma padronizada:

- **HTTPException**: Retorna o status e detalhe do erro.
- **Exception**: Captura erros inesperados, retorna 500 com mensagem genérica.
- **401 Unauthorized**: Retorna mensagem específica para falha de autenticação JWT.

---

## Fluxo de Requisição (Texto)

1. Requisição HTTP chega à aplicação.
2. Passa pelo CORSMiddleware (verifica e aplica regras de CORS).
3. Passa pelo AuthMiddleware (valida JWT).
4. Se autorizado, roteia para o endpoint correto (auth ou upload).
5. Endpoint processa a lógica de negócio.
6. Se ocorrer exceção, tratadores globais entram em ação.
7. Resposta HTTP é enviada ao cliente.

---

## Fluxo de Requisição (Diagrama Mermaid)

mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant CORS as CORSMiddleware
    participant Auth as AuthMiddleware
    participant Router as Endpoint Router
    participant Handler as ExceptionHandler
    Client->>FastAPI: HTTP Request
    FastAPI->>CORS: Passa pelo CORSMiddleware
    CORS->>Auth: Passa pelo AuthMiddleware
    Auth->>Router: Roteamento para endpoint
    Router->>Handler: (Se exceção)
    Router-->>Client: HTTP Response
    Handler-->>Client: HTTP Error Response


---

## Exemplos Práticos

### 1. Requisição bem-sucedida com JWT válido

bash
curl -H "Authorization: Bearer <token_válido>" http://localhost:8000/upload/arquivo -F "file=@exemplo.txt"


### 2. Requisição rejeitada por token inválido (401)

bash
curl -H "Authorization: Bearer token_invalido" http://localhost:8000/upload/arquivo -F "file=@exemplo.txt"
# Resposta: {"detail": "Token JWT inválido ou ausente."}


### 3. Tratamento de HTTPException

python
import requests
r = requests.get('http://localhost:8000/upload/arquivo_inexistente', headers={"Authorization": "Bearer <token_válido>"})
print(r.status_code, r.json())
# Exemplo de resposta: 404 {'detail': 'Not Found'}


### 4. Erro interno (500)

python
import requests
r = requests.get('http://localhost:8000/rota_que_gera_erro', headers={"Authorization": "Bearer <token_válido>"})
print(r.status_code, r.json())
# Exemplo de resposta: 500 {'detail': 'Erro interno do servidor.'}


---

## Arquitetura de Componentes (Mermaid)

mermaid
graph LR
    A[FastAPI App]
    B[CORSMiddleware]
    C[AuthMiddleware]
    D[Auth Router]
    E[Upload Router]
    F[Exception Handlers]
    A --> B
    B --> C
    C --> D
    C --> E
    A --> F


---

## Considerações de Segurança e Boas Práticas

- **Restrinja CORS em produção**: Defina `allow_origins` para apenas domínios confiáveis.
- **Proteja rotas sensíveis**: Garanta que apenas endpoints públicos estejam acessíveis sem JWT.
- **Tratamento de erros**: Não exponha detalhes sensíveis em mensagens de erro.
- **Valide e sanitize uploads**: Implemente validação de arquivos no upload_router.
- **Atualize dependências**: Mantenha as bibliotecas sempre atualizadas para evitar vulnerabilidades.

---

> Para dúvidas ou sugestões, consulte o código-fonte ou entre em contato com o time de backend.
