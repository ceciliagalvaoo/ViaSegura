#!/bin/bash
# Script para baixar arquivo grande do Google Drive usando gdown

FILE_ID="189t-7al_kQMAT9XFkQ-tBhib3yPaHKGs"
OUTPUT_FILE="data/acidente_transito.kmz"

# Criar diretório se não existir
mkdir -p data

# Instalar gdown se não estiver instalado
pip install gdown

# Baixar do Google Drive se arquivo não existir
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "Baixando arquivo de acidentes do Google Drive (326MB)..."
    gdown "https://drive.google.com/uc?id=${FILE_ID}" -O "$OUTPUT_FILE" --fuzzy
    echo "Download concluído!"
else
    echo "Arquivo já existe, pulando download."
fi
