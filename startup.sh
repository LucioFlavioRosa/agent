#!/bin/bash

# --- PASSO 1: INSTALAÇÃO DE DEPENDÊNCIAS DE SISTEMA (GIT) ---
# É uma boa prática atualizar a lista de pacotes antes de instalar.
echo "Atualizando a lista de pacotes..."
apt-get update

# Instala o Git. A flag '-y' confirma automaticamente a instalação.
echo "Instalando o Git..."
apt-get install -y git


# --- PASSO 2: INSTALAÇÃO DO .NET SDK ---
echo "Iniciando verificação/instalação do .NET SDK..."
DOTNET_ROOT=/home/site/dotnet
DOTNET_INSTALL_SCRIPT_URL=https://dot.net/v1/dotnet-install.sh
DOTNET_VERSION=9.0

if [ ! -d "$DOTNET_ROOT" ]; then
  echo "Instalando .NET SDK v${DOTNET_VERSION}..."
  wget $DOTNET_INSTALL_SCRIPT_URL -O dotnet-install.sh
  chmod +x dotnet-install.sh
  ./dotnet-install.sh --channel $DOTNET_VERSION --install-dir $DOTNET_ROOT
  rm dotnet-install.sh
else
  echo ".NET SDK v${DOTNET_VERSION} já está instalado em ${DOTNET_ROOT}."
fi


# --- PASSO 3: CONFIGURAÇÃO DO AMBIENTE ---
echo "Configurando o PATH..."
export PATH=$PATH:$DOTNET_ROOT
echo "PATH configurado para incluir a CLI do .NET."
echo "Versão do .NET detectada: $(dotnet --version)"


# --- PASSO 4: INICIALIZAÇÃO DA SUA APLICAÇÃO PYTHON ---
echo "Iniciando a aplicação com Gunicorn/Uvicorn..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker mcp_server_fastapi:app
