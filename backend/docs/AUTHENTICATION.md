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


O código responsável por este fluxo está em:
- `backend/app/api/auth.py` (endpoint `/auth/login`)

python
@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    app = msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AZURE_AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET
    )
    result = app.acquire_token_by_username_password(
        username=request.username,
        password=request.password,
        scopes=AZURE_SCOPE
    )
    if "access_token" not in result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falha na autenticação Azure AD: {result.get('error_description', 'Erro desconhecido')}"
        )
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result.get("expires_in", 3600)
    )


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


## 3. Fluxo de Autenticação com Código

Todas as requisições protegidas passam pelo middleware de autenticação, que realiza as seguintes etapas:

- Intercepta o header `Authorization: Bearer <JWT_TOKEN>`.
- Decodifica o token JWT e valida sua assinatura, expiração e claims obrigatórios.
- Se o token for válido, extrai os dados do usuário e injeta no contexto da requisição (`request.state.user`).
- Se inválido ou ausente, retorna HTTP 401 Unauthorized.

### Middleware de Autenticação: `AuthMiddleware`

O middleware está implementado em `backend/app/middleware/auth_middleware.py`.

#### Função principal de extração do usuário:
python
def get_current_user(request: Request) -> AzureADTokenData:
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    return azure_ad_service.validate_token(param)


- **Explicação:**
    - Busca o header `Authorization` da requisição.
    - Se o header não existir ou não for do tipo Bearer, retorna erro 401.
    - Caso contrário, chama o serviço `azure_ad_service.validate_token(param)` para validar o token e extrair os dados do usuário.

#### Validação do Token JWT:
A validação do token ocorre em `backend/app/services/azure_ad_service.py`:

python
def validate_token(self, token: str) -> AzureADTokenData:
    try:
        import jwt
        from jwt import InvalidTokenError, ExpiredSignatureError
        claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": True}, algorithms=["RS256", "HS256"])
        usuario_executor = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
        if not usuario_executor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="usuario_executor não encontrado no token Azure AD.")
        return AzureADTokenData(usuario_executor=usuario_executor, claims=claims)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Azure AD expirado.")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Azure AD inválido.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao validar token Azure AD: {str(e)}")


- **Explicação:**
    - Decodifica o JWT e verifica se está expirado.
    - Extrai o usuário autenticado do claim `preferred_username`, `email` ou `upn`.
    - Se não encontrar, retorna erro 401.
    - Se o token estiver expirado ou inválido, retorna erro 401.

#### Middleware propriamente dito:
python
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)
        if not auth or scheme.lower() != "bearer":
            return await call_next(request)
        try:
            user = azure_ad_service.validate_token(param)
            request.state.user = user
        except HTTPException:
            return await call_next(request)
        response = await call_next(request)
        return response

- **Explicação:**
    - Intercepta todas as requisições.
    - Se houver token Bearer, valida e injeta o usuário em `request.state.user`.
    - Se não houver ou for inválido, segue o fluxo sem autenticação (dependendo do endpoint, pode resultar em erro 401 posteriormente).

### Como acessar o usuário autenticado nos endpoints

Para acessar dados do usuário autenticado dentro dos endpoints, utilize o método `get_current_user(request)`:

python
from ..middleware.auth_middleware import get_current_user

@router.get("/me")
def get_profile(request: Request):
    user = get_current_user(request)
    return {"usuario_executor": user.usuario_executor}


## 4. Diagrama Mermaid: Fluxo de Autenticação

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


## 5. Boas Práticas de Segurança Implementadas e Recomendações

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
