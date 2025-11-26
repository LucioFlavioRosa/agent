# Backend API - Visão Geral
        
Este repositório implementa o backend para upload de arquivos DOCX, autenticação via Azure AD/JWT, integração com Azure Blob Storage e comunicação com MCP Server para geração de relatórios.

## Principais Funcionalidades\n- Autenticação de usuários via Azure AD/JWT
        - Upload de arquivos DOCX
        - Extração de texto dos arquivos DOCX
        - Armazenamento dos arquivos no Azure Blob Storage
        - Comunicação com MCP Server para iniciar análise e gerar relatório
        
## Pré-requisitos
        - Python 3.9+
        - Conta Azure Storage configurada
        - MCP Server acessível
        
## Instalação
        1. Clone o repositório
        2. Instale as dependências:
        bash
        pip install -r requirements.txt  
        3. Configure as variáveis de ambiente no arquivo `.env` conforme documentação
        
## Execução\nbash\nuvicorn backend.app.main:app --reload\
        
## Estrutura de Pastas
        
        backend/
        ├── app/
        │   ├── api/
        │   ├── core/
        │   ├── middleware/
        │   ├── models/
        │   ├── services/
        │   ├── utils/
        │   └── main.py
        ├── docs/
        │   ├── ARCHITECTURE.md\
        │   ├── API_FLOW.md\
        │   └── AUTHENTICATION.md
        ├── requirements.txt
        └── tests
        
## Endpoints Principais
        - `POST /auth/login` - Autenticação Azure AD
        - `POST /upload/docx` - Upload de arquivo DOCX
        
## Documentação Detalhada
        - [Arquitetura](docs/ARCHITECTURE.md)
        - [Fluxo de API](docs/API_FLOW.md)
        - [Autenticação](docs/AUTHENTICATION.md)
        
## Diagrama de Alto Nível
        
        ```mermaid
        flowchart TD
        FE[Frontend] --> API[Backend API]
        API -->|Autenticação| AzureAD[Azure AD]
        API -->|Upload DOCX| Blob[Azure Blob Storage]
        API -->|Start Analysis| MCP[MCP Server]
        MCP -->|job_id| API
        API --> FE
        ```
        
