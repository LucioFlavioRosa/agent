#!/bin/bash

# Garante que o sistema de pacotes esteja atualizado e instala o git
# O comando -y responde 'sim' para qualquer pergunta, automatizando a instalação.
echo "--- Atualizando pacotes e instalando o git ---"
apt-get update && apt-get install -y git
echo "--- Git instalado com sucesso. ---"

# Executa o comando original para iniciar o seu servidor FastAPI
echo "--- Iniciando o servidor Gunicorn ---"
gunicorn -w 4 -k uvicorn.workers.UvicornWorker mcp_server_fastapi:app
