# Documentação Detalhada: Endpoint `/upload/docx`

## Visão Geral
O arquivo `backend/app/api/upload.py` implementa o endpoint principal para upload de arquivos DOCX no backend. Este endpoint é o ponto de entrada para o fluxo de upload, extração de texto, armazenamento no Azure Blob Storage e disparo de análise via MCP Server. Ele é fundamental para a integração entre frontend, autenticação, processamento de arquivos e sistemas externos.

---

## Quem chama este endpoint?
- **Frontend Web ou Aplicativo:**
  - O endpoint `/upload/docx` é chamado diretamente pelo frontend da aplicação, geralmente via um formulário de upload, onde o usuário seleciona um arquivo `.docx` e preenche informações como projeto, nome da análise e tipo de análise.
  - A requisição deve conter um token JWT válido no header `Authorization`, obtido previamente via login pelo endpoint `/auth/login`.

---

## Funcionamento e Papel do Código
O arquivo `upload.py` define o endpoint `/upload/docx` e orquestra todo o fluxo de recebimento, validação, processamento e encaminhamento do arquivo DOCX para análise. Seu papel é garantir que apenas usuários autenticados possam realizar uploads, que o arquivo seja válido, que o texto seja extraído corretamente, que o arquivo seja salvo no blob storage e que o MCP Server seja acionado para processar a análise.

### Passo a Passo do Fluxo
1. **Recebimento da Requisição:**
   - O endpoint recebe uma requisição POST multipart contendo o arquivo DOCX (`file`), o nome do projeto (`projeto`), o nome da análise (`analysis_name`) e o tipo de análise (`analysis_type`).
   - O header `Authorization: Bearer <JWT>` é obrigatório.

2. **Autenticação:**
   - O parâmetro `current_user` é resolvido via `Depends(get_current_user)`, que utiliza o middleware de autenticação para validar o JWT e extrair o usuário autenticado.
   - Se o usuário não estiver autenticado, retorna HTTP 401.

3. **Validação do Arquivo:**
   - O código verifica se o arquivo enviado possui a extensão `.docx`. Caso contrário, retorna HTTP 400.

4. **Extração de Texto:**
   - O arquivo é processado pelo serviço `extract_text_from_docx`, que lê o conteúdo do DOCX e extrai todo o texto, retornando-o como string.
   - Se houver erro na extração, retorna HTTP 400.

5. **Upload para Azure Blob Storage:**
   - O arquivo é salvo no Azure Blob Storage em background, utilizando o serviço `upload_docx_to_blob`. O caminho do blob é construído com base no usuário, projeto e nome da análise.
   - O endpoint retorna imediatamente a URL do blob, mesmo que o upload ainda esteja em andamento.

6. **Montagem do Payload para MCP Server:**
   - Um payload do tipo `MCPStartAnalysisPayload` é montado contendo o tipo de análise, texto extraído, projeto, nome da análise e usuário executor.

7. **Chamada ao MCP Server:**
   - O serviço `MCPClientService` é utilizado para enviar o payload ao MCP Server, disparando o início da análise.
   - O MCP Server retorna um `job_id` que identifica a análise iniciada.

8. **Resposta ao Frontend:**
   - O endpoint retorna um objeto `UploadDocxResponse` com o `job_id`, a URL do arquivo no blob storage e uma mensagem de sucesso.

---

## Interações e Dependências
O endpoint `/upload/docx` interage diretamente com diversos componentes do backend:

- **AuthMiddleware / get_current_user:**
  - Valida o JWT e injeta o usuário autenticado no contexto da requisição.
- **BlobStorageService (`upload_docx_to_blob`):**
  - Realiza o upload do arquivo DOCX para o Azure Blob Storage.
- **DocxParserService (`extract_text_from_docx`):**
  - Extrai o texto do arquivo DOCX enviado.
- **MCPClientService:**
  - Envia o payload de análise para o MCP Server e recebe o `job_id`.
- **Modelos Pydantic:**
  - Define os contratos de entrada (`UploadDocxRequest`) e saída (`UploadDocxResponse`).

---

## Diagrama de Sequência (Mermaid)
mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as /upload/docx Endpoint
    participant MW as AuthMiddleware
    participant Blob as BlobStorageService
    participant Parser as DocxParserService
    participant MCP as MCPClientService

    FE->>API: POST /upload/docx (arquivo + dados + JWT)
    API->>MW: Valida JWT
    MW-->>API: Usuário autenticado
    API->>API: Valida extensão do arquivo
    API->>Parser: Extrai texto do DOCX
    Parser-->>API: Texto extraído
    API->>Blob: Upload DOCX (background)
    Blob-->>API: URL do blob
    API->>MCP: POST /start-analysis (payload)
    MCP-->>API: job_id
    API-->>FE: job_id, blob_url, mensagem


---

## Diagrama de Fluxo de Dados (Mermaid)
mermaid
graph TD
    FE[Frontend] -->|Arquivo DOCX + JWT| API[/upload/docx]
    API --> MW[AuthMiddleware]
    MW -->|Usuário autenticado| API
    API -->|Validação| API
    API --> Parser[DocxParserService]
    Parser -->|Texto extraído| API
    API --> Blob[BlobStorageService]
    Blob -->|URL do arquivo| API
    API --> MCP[MCPClientService]
    MCP -->|job_id| API
    API --> FE


---

## Exemplos de Requisição e Resposta

### Requisição (Frontend → Backend)
http
POST /upload/docx
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data

file: <arquivo.docx>
projeto: "ProjetoX"
analysis_name: "Reuniao_01"
analysis_type: "criacao_epicos_azure_devops"


### Resposta (Backend → Frontend)

{
  "job_id": "abc-123",
  "blob_url": "https://blobstorage.azure.com/user/projetoX/arquivos_recebidos/docx/Reuniao_01.docx",
  "message": "Arquivo recebido, salvo e análise iniciada com sucesso."
}


---

## Referências Diretas ao Código
- **Arquivo:** [`backend/app/api/upload.py`](../app/api/upload.py)
- **Função principal:**
  - `@router.post("/upload/docx", ...)` → `async def upload_docx(...)`
- **Dependências:**
  - `from ..middleware.auth_middleware import get_current_user`
  - `from ..services.blob_storage_service import upload_docx_to_blob`
  - `from ..services.docx_parser_service import extract_text_from_docx`
  - `from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload`

---

## Resumo do Papel do Endpoint
O endpoint `/upload/docx` é o núcleo do fluxo de upload e análise de arquivos DOCX no backend. Ele garante segurança (autenticação), validação, processamento eficiente do arquivo, armazenamento seguro e integração transparente com o MCP Server para geração de relatórios. Sua atuação é fundamental para a experiência do usuário e para o funcionamento integrado da solução.
