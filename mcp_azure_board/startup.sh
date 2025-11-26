#!/bin/bash
set -e

# Ativar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi

# Instalar dependências
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Exportar variáveis de ambiente necessárias (exemplo)
export AZURE_STORAGE_CONTAINER_NAME="your_container_name"
export AZURE_STORAGE_ACCOUNT_URL="your_account_url"
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"

# Iniciar servidor FastAPI
uvicorn mcp_azure_board.mcp_server_fastapi:app --host 0.0.0.0 --port 8000
