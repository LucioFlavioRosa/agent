# Autenticação Backend - Azure AD & JWT

Este documento descreve o funcionamento do sistema de autenticação do backend, detalhando o fluxo de login, estrutura do token JWT, validação pelo middleware, extração do usuário autenticado e recomendações de segurança. O objetivo é fornecer uma visão clara e objetiva dos pontos essenciais para garantir a proteção dos endpoints e a identificação segura dos usuários.

## 1. Fluxo de Login (POST /auth/login)

O login é realizado via endpoint `/auth/login`, que autentica o usuário utilizando Azure Active Directory (Azure AD):

- O frontend envia uma requisição POST contendo `username` e `password`.
- O backend utiliza a biblioteca MSAL para autenticar as credenciais no Azure AD.
- Se autenticado com sucesso, retorna um token JWT válido para o usuário.
- Se falhar, retorna HTTP 401 com mensagem de erro.

**Exemplo de requisição:**
http
POST /auth/login
Content-Type: application/json
{
  "username": "usuario@example.com",
  "password": "senha_segura"
}


**Exemplo de resposta:**

{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600
}


## 2. Estrutura do Token JWT e Claims Utilizados

O token JWT emitido pelo Azure AD contém diversos claims que identificam o usuário e garantem a segurança da sessão. Os principais são:

- `sub`: Identificador único do usuário (Subject)
- `usuario_executor`: Email ou username do usuário autenticado
- `exp`: Timestamp de expiração do token
- `iss`: Emissor do token (Issuer)
- `aud`: Destinatário do token (Audience)
- Outros claims: `preferred_username`, `email`, `roles`, etc.

**Exemplo de payload do JWT:**

{
  "sub": "a1b2c3d4",
  "usuario_executor": "usuario@example.com",
  "exp": 1712345678,
  "iss": "https://login.microsoftonline.com/<tenant_id>",
  "aud": "api://backend-app",
  "preferred_username": "usuario@example.com",
  "email": "usuario@example.com",
  "roles": ["user"]
}


## 3. Validação do Token pelo Middleware (AuthMiddleware)

Todas as requisições protegidas passam pelo middleware de autenticação, que realiza as seguintes etapas:

- Intercepta o header `Authorization: Bearer <JWT_TOKEN>`.
- Decodifica o token JWT e valida sua assinatura, expiração e claims obrigatórios.
- Se o token for válido, extrai os dados do usuário e injeta no contexto da requisição (`request.state.user`).
- Se inválido ou ausente, retorna HTTP 401 Unauthorized.

**Pseudocódigo do fluxo:**
python
auth = request.headers.get("Authorization")
scheme, param = get_authorization_scheme_param(auth)
if not auth or scheme.lower() != "bearer":
    raise HTTPException(status_code=401)
user = azure_ad_service.validate_token(param)
request.state.user = user


## 4. Extração do Usuário Autenticado nos Endpoints Protegidos

Para acessar dados do usuário autenticado dentro dos endpoints, utilize o método `get_current_user(request)`:

- Recebe o objeto `Request`.
- Retorna os dados do usuário extraídos do token JWT (ex: `usuario_executor`, `sub`).
- Permite associar ações e permissões ao usuário logado.

**Exemplo de uso em endpoint:**
python
from ..middleware.auth_middleware import get_current_user

@router.get("/me")
def get_profile(request: Request):
    user = get_current_user(request)
    return {"usuario_executor": user.usuario_executor}


## 5. Diagrama Mermaid: Fluxo de Autenticação

mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as Backend API
    participant AzureAD as Azure AD

    FE->>API: POST /auth/login (credenciais)
    API->>AzureAD: Valida credenciais
    AzureAD-->>API: Token JWT
    API-->>FE: access_token
    FE->>API: Requisições protegidas (com JWT)
    API->>API: Middleware valida JWT
    API-->>FE: Dados do usuário autenticado ou erro


## 6. Boas Práticas de Segurança Implementadas e Recomendações

- **Validação robusta do JWT:** Assinatura, expiração e claims obrigatórios são verificados em todas as requisições protegidas.
- **Uso de HTTPS:** Todo o tráfego entre frontend, backend e Azure AD deve ser protegido por TLS.
- **Segregação de ambientes:** Variáveis sensíveis (segredos, client_id, etc.) são carregadas via `.env` e nunca expostas em código.
- **Expiração curta dos tokens:** Tokens possuem tempo de vida limitado para reduzir riscos.
- **Proteção contra ataques de replay:** Tokens expirados ou reutilizados são rejeitados.
- **Recomendações adicionais:**
  - Nunca logar tokens ou credenciais em arquivos de log.
  - Revogar tokens comprometidos imediatamente.
  - Monitorar tentativas de login e acessos suspeitos.

---

**Resumo:**
O sistema de autenticação do backend garante que apenas usuários autenticados via Azure AD possam acessar endpoints protegidos, utilizando JWTs validados por middleware dedicado. O fluxo é seguro, eficiente e facilmente auditável, com boas práticas de segurança implementadas em todas as etapas.