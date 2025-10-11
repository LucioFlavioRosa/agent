#!/bin/bash

# --- PASSO 1: INSTALAÇÃO DO .NET SDK ---

# Configurações
# Usamos /home/site/dotnet porque o diretório /home é persistente entre reinicializações no App Service
DOTNET_ROOT=/home/site/dotnet
DOTNET_INSTALL_SCRIPT_URL=https://dot.net/v1/dotnet-install.sh
DOTNET_VERSION=9.0 # <--- ATUALIZADO PARA A VERSÃO SOLICITADA

# Verifica se o SDK já foi instalado para não fazer o download todas as vezes
if [ ! -d "$DOTNET_ROOT" ]; then
  echo "Instalando .NET SDK v${DOTNET_VERSION}..."
  # Baixa o script oficial de instalação da Microsoft
  wget $DOTNET_INSTALL_SCRIPT_URL -O dotnet-install.sh
  chmod +x dotnet-install.sh
  
  # Executa a instalação na pasta especificada
  ./dotnet-install.sh --channel $DOTNET_VERSION --install-dir $DOTNET_ROOT
  
  # Limpa o arquivo de script após a instalação
  rm dotnet-install.sh
else
  echo ".NET SDK v${DOTNET_VERSION} já está instalado em ${DOTNET_ROOT}."
fi

# --- PASSO 2: CONFIGURAÇÃO DO AMBIENTE ---

# Adiciona a CLI do 'dotnet' ao PATH do sistema para esta sessão.
# Este passo é CRÍTICO para que o seu script Python (via subprocess) encontre o comando 'dotnet'.
export PATH=$PATH:$DOTNET_ROOT
echo "PATH configurado para incluir a CLI do .NET."

# Verificação opcional (aparecerá nos logs de inicialização)
echo "Versão do .NET detectada: $(dotnet --version)"


# --- PASSO 3: INICIALIZAÇÃO DA SUA APLICAÇÃO PYTHON ---

# O comando final do script deve ser o comando que inicia o seu servidor web.
# Substituímos o comando genérico pelo seu comando exato do Gunicorn/Uvicorn.
echo "Iniciando a aplicação com Gunicorn/Uvicorn..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker mcp_server_fastapi:app
