# Documentação Detalhada: backend/main.py

## Índice
1. [Visão Geral](#visão-geral)
2. [Importações e Finalidades](#importações-e-finalidades)
3. [Configuração da Instância FastAPI](#configuração-da-instância-fastapi)
4. [Middleware CORS](#middleware-cors)
5. [Middleware de Autenticação JWT (AuthMiddleware)](#middleware-de-autenticação-jwt-authmiddleware)
6. [Função get_current_user](#função-get_current_user)
7. [Endpoint /auth/login](#endpoint-authlogin)
8. [Endpoint /upload/docx](#endpoint-uploaddocx)
9. [Tratadores de Exceções Globais](#tratadores-de-exceções-globais)
10. [Diagramas Mermaid](#diagramas-mermaid)
11. [Exemplos Práticos de Requisições e Respostas](#exemplos-práticos-de-requisições-e-respostas)
12. [Considerações de Segurança e Boas Práticas](#considerações-de-segurança-e-boas-práticas)
13. [Referências Diretas](#referências-diretas)

---

## Visão Geral
O arquivo `backend/main.py` é o ponto de entrada unificado da aplicação FastAPI. Ele centraliza a configuração da API, define middlewares críticos (CORS e autenticação JWT), implementa endpoints principais (`/auth/login` e `/upload/docx`), e registra tratadores globais de exceções. Todo o fluxo de autenticação, upload, processamento e integração com serviços externos é orquestrado a partir deste arquivo.

---

## Importações e Finalidades
- **os**: Acesso a variáveis de ambiente.
- **fastapi, Request, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, status**: Componentes principais do FastAPI para definição de endpoints, manipulação de requisições, exceções e dependências.
- **fastapi.responses.JSONResponse**: Retorno customizado de respostas JSON.
- **fastapi.middleware.cors.CORSMiddleware**: Middleware para controle de CORS.
- **fastapi.security.utils.get_authorization_scheme_param**: Utilitário para extrair o esquema do header Authorization.
- **starlette.middleware.base.BaseHTTPMiddleware**: Base para criação de middlewares customizados.
- **typing.Optional**: Tipagem opcional.
- **msal**: Biblioteca Microsoft para autenticação Azure AD.
- **pydantic.BaseModel**: Modelos de dados para validação e documentação automática.
- **backend.app.core.config.settings**: Objeto de configuração central da aplicação.
- **backend.app.services.blob_storage_service.upload_docx_to_blob**: Serviço para upload de arquivos ao Azure Blob Storage.
- **backend.app.services.docx_parser_service.extract_text_from_docx**: Serviço para extração de texto de arquivos DOCX.
- **backend.app.services.mcp_client_service.MCPClientService, MCPStartAnalysisPayload**: Serviço de comunicação com MCP Server.
- **backend.app.services.azure_ad_service.AzureADService**: Serviço de validação de tokens Azure AD.

---

## Configuração da Instância FastAPI
A aplicação é instanciada com título, descrição e versão, facilitando a documentação automática e a identificação da API.
python
app = FastAPI(title="Backend API", description="Backend para upload e autenticação JWT", version="1.0.0")


---

## Middleware CORS
O CORS (Cross-Origin Resource Sharing) é configurado para permitir requisições de qualquer origem (`allow_origins=["*"]`).

python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

- **Implicações de segurança:**
  - Permite que qualquer frontend acesse a API. Ideal para desenvolvimento, mas deve ser restrito em produção para domínios confiáveis.

---

## Middleware de Autenticação JWT (AuthMiddleware)
O middleware intercepta todas as requisições e, se houver header Authorization do tipo Bearer, valida o token JWT usando o serviço AzureADService. Se válido, injeta o usuário autenticado em `request.state.user`.

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

- **Fluxo:**
  - Se não houver Authorization Bearer, segue sem autenticação.
  - Se houver, tenta validar e injeta o usuário.
  - Falha na validação não bloqueia a requisição imediatamente (validação final ocorre no endpoint via Depends).

---

## Função get_current_user
Valida o token JWT da requisição e retorna os dados do usuário autenticado. Usada como dependência nos endpoints protegidos.

python
def get_current_user(request: Request):
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    return azure_ad_service.validate_token(param)

- **Papel:**
  - Garante que endpoints protegidos só sejam acessados por usuários autenticados.
  - Retorna um objeto com os dados do usuário extraídos do token.

---

## Endpoint /auth/login
Realiza autenticação do usuário via Azure AD utilizando a biblioteca MSAL. Recebe username e password, retorna access_token JWT, tipo de token e tempo de expiração.

python
@app.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", settings.AZURE_AD_CLIENT_ID)
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", settings.AZURE_AD_TENANT_ID)
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", settings.AZURE_AD_CLIENT_SECRET)
    AZURE_SCOPE = [os.environ.get("AZURE_SCOPE", "User.Read")]
    app_msal = msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AZURE_AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET
    )
    result = app_msal.acquire_token_by_username_password(
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

- **Fluxo:**
  1. Recebe credenciais do usuário.
  2. Autentica no Azure AD via MSAL.
  3. Se sucesso, retorna JWT e dados de expiração.
  4. Se falha, retorna 401 com mensagem de erro.

---

## Endpoint /upload/docx
Endpoint assíncrono para upload de arquivos DOCX, protegido por autenticação JWT.

python
@app.post("/upload/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...),
    analysis_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    if not usuario_executor:
        raise HTTPException(status_code=401, detail="Usuário não autenticado no token.")
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    try:
        texto_extraido = await extract_text_from_docx(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_name}.docx"
    blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    payload = MCPStartAnalysisPayload(
        analysis_type=analysis_type,
        instrucoes_extras=texto_extraido,
        projeto=projeto,
        analysis_name=analysis_name,
        usuario_executor=usuario_executor
    )
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(payload)
        job_id = mcp_response.job_id
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com MCP Server: {str(e)}")
    return UploadDocxResponse(job_id=job_id, blob_url=blob_url, message="Arquivo recebido, salvo e análise iniciada com sucesso.")


- **Fluxo detalhado:**
  1. Valida usuário autenticado via JWT.
  2. Valida extensão do arquivo (`.docx`).
  3. Extrai texto do arquivo usando serviço dedicado.
  4. Salva arquivo no Azure Blob Storage (em background).
  5. Monta payload para MCP Server.
  6. Dispara análise no MCP Server e recebe job_id.
  7. Retorna job_id, URL do blob e mensagem de sucesso.

---

## Tratadores de Exceções Globais
Tratadores globais garantem respostas padronizadas para erros comuns e inesperados.

python
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."}
    )

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"detail": "Token JWT inválido ou ausente."}
    )

- **Cobre:**
  - HTTPException: Erros conhecidos (ex: 400, 401, 404).
  - Exception: Erros inesperados (500).
  - 401: Falha de autenticação JWT.

---

## Diagramas Mermaid

### 1. Fluxo Completo de Requisição
mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant CORS as CORSMiddleware
    participant Auth as AuthMiddleware
    participant Endpoint as Endpoint
    participant Blob as BlobStorageService
    participant Parser as DocxParserService
    participant MCP as MCPClientService
    Client->>FastAPI: HTTP Request
    FastAPI->>CORS: Passa pelo CORSMiddleware
    CORS->>Auth: Passa pelo AuthMiddleware
    Auth->>Endpoint: Roteamento para endpoint
    Endpoint->>Parser: Extrai texto do DOCX
    Parser-->>Endpoint: Texto extraído
    Endpoint->>Blob: Upload DOCX
    Blob-->>Endpoint: URL do arquivo
    Endpoint->>MCP: POST /start-analysis
    MCP-->>Endpoint: job_id
    Endpoint-->>Client: Resposta JSON


### 2. Fluxo de Autenticação
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


---

## Exemplos Práticos de Requisições e Respostas

### 1. Login
**Requisição:**
http
POST /auth/login
Content-Type: application/json
{
  "username": "usuario@example.com",
  "password": "senha_segura"
}

**Resposta:**

{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600
}


### 2. Upload de Arquivo DOCX
**Requisição:**
http
POST /upload/docx
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data
file: <arquivo.docx>
projeto: "ProjetoX"
analysis_name: "Reuniao_01"
analysis_type: "criacao_epicos_azure_devops"

**Resposta:**

{
  "job_id": "abc-123",
  "blob_url": "https://blobstorage.azure.com/user/projetoX/arquivos_recebidos/docx/Reuniao_01.docx",
  "message": "Arquivo recebido, salvo e análise iniciada com sucesso."
}


### 3. Erros Comuns
- **Token inválido ou ausente:**

{
  "detail": "Token JWT inválido ou ausente."
}

- **Arquivo não .docx:**

{
  "detail": "Apenas arquivos .docx são permitidos."
}

- **Erro interno:**

{
  "detail": "Erro interno do servidor."
}


---

## Considerações de Segurança e Boas Práticas
- **CORS:** Permissivo em desenvolvimento, restrinja em produção.
- **JWT:** Tokens validados em todas as requisições protegidas.
- **Tratamento de erros:** Mensagens genéricas para erros inesperados (500).
- **Variáveis sensíveis:** Carregadas via ambiente/configuração, nunca hardcoded.
- **Uploads:** Apenas arquivos .docx permitidos.
- **Background tasks:** Uploads para blob são feitos em background para não bloquear resposta ao usuário.
- **Segregação de responsabilidades:** Serviços externos (Blob, MCP, Azure AD) são abstraídos em módulos dedicados.

---

## Referências Diretas
- **Serviço de autenticação:** `backend.app.services.azure_ad_service.AzureADService`
- **Serviço de upload:** `backend.app.services.blob_storage_service.upload_docx_to_blob`
- **Serviço de extração de texto:** `backend.app.services.docx_parser_service.extract_text_from_docx`
- **Serviço MCP:** `backend.app.services.mcp_client_service.MCPClientService`
- **Configuração:** `backend.app.core.config.settings`
- **Middleware:** `AuthMiddleware` (definido inline)
- **Função de dependência:** `get_current_user`

---

> Para dúvidas, consulte também os arquivos de serviço e a documentação de arquitetura geral.