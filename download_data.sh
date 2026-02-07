#!/bin/bash
# Script para baixar arquivo grande do Google Drive

FILE_ID="189t-7al_kQMAT9XFkQ-tBhib3yPaHKGs"
OUTPUT_FILE="data/acidente_transito.kmz"

# Criar diretório se não existir
mkdir -p data

# Baixar do Google Drive se arquivo não existir
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "Baixando arquivo de acidentes do Google Drive..."
    wget --no-check-certificate "https://drive.google.com/uc?export=download&id=${FILE_ID}" -O "$OUTPUT_FILE"
    echo "Download concluído!"
else
    echo "Arquivo já existe, pulando download."
fi
