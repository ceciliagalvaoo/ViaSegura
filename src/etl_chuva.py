"""
Módulo para processamento de dados de chuva de São Paulo.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import re


def extrair_metadados(linhas_iniciais):
    """Extrai metadados do cabeçalho do arquivo de chuva."""
    metadata = {}
    for linha in linhas_iniciais:
        if ':' in linha:
            chave, valor = linha.split(':', 1)
            chave = chave.strip().replace('PREFIXO', 'prefixo').replace('NOME DO POSTO', 'nome_posto').replace('MUNICÍPIO', 'municipio')
            metadata[chave.strip()] = valor.strip()
    return metadata


def converter_coordenadas(coord_str):
    """Converte coordenadas do formato grau/minuto/segundo para decimal."""
    try:
        # Remove espaços e extrai números
        match = re.match(r"(\d+)°(\d+)'(\d+)\"", coord_str.strip())
        if match:
            graus, minutos, segundos = map(int, match.groups())
            decimal = graus + minutos/60 + segundos/3600
            return decimal
        return None
    except:
        return None


def processar_arquivo_chuva(filepath):
    """
    Processa o arquivo de chuva de São Paulo e retorna um DataFrame estruturado.
    
    Args:
        filepath: Caminho para o arquivo CSV
        
    Returns:
        DataFrame com dados de chuva processados em formato longo
    """
    # Ler metadados (primeiras 7 linhas)
    with open(filepath, 'r', encoding='latin-1') as f:
        linhas_iniciais = [f.readline() for _ in range(7)]
    
    metadata = extrair_metadados(linhas_iniciais)
    
    # Ler dados de chuva (pula 12 linhas de cabeçalho)
    df = pd.read_csv(filepath, sep=';', skiprows=12, encoding='latin-1')
    
    # Limpar BOM se presente
    df.columns = df.columns.str.replace('\ufeff', '').str.strip()
    
    # IMPORTANTE: Renomear colunas duplicadas (múltiplos '0,0' etc)
    # Vamos forçar nomes únicos baseados na posição
    new_cols = []
    for i, col in enumerate(df.columns):
        if i == 0:
            new_cols.append('Mês/Ano')
        elif i <= 31:
            new_cols.append(str(i))  # Dias 1-31
        else:
            new_cols.append(col)  # Colunas especiais (Chuva máxima, Chuva total)
    
    df.columns = new_cols
    
    # Substituir vírgulas por pontos e '---' por vazio em cada coluna
    for col in df.columns:
        if col != 'Mês/Ano':
            df[col] = (
                df[col]
                .astype(str)
                .str.replace('---', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Transformar formato largo → longo (dias 1-31)
    dia_cols = [str(i) for i in range(1, 32) if str(i) in df.columns]
    
    df_longo = df.melt(
        id_vars=['Mês/Ano'], 
        value_vars=dia_cols,
        var_name='dia',
        value_name='chuva_mm'
    )
    
    # Parsear data (formato: MM/YYYY)
    df_longo['mes'] = df_longo['Mês/Ano'].str.split('/').str[0].astype(int)
    df_longo['ano'] = df_longo['Mês/Ano'].str.split('/').str[1].astype(int)
    df_longo['dia'] = df_longo['dia'].astype(int)
    
    # Criar coluna data
    df_longo['data'] = pd.to_datetime(
        df_longo[['ano', 'mes', 'dia']].rename(columns={'ano': 'year', 'mes': 'month', 'dia': 'day'}),
        errors='coerce'
    )
    
    # Converter chuva para numérico
    df_longo['chuva_mm'] = pd.to_numeric(df_longo['chuva_mm'], errors='coerce')
    
    # Remover linhas com datas inválidas ou chuva NaN
    df_longo = df_longo.dropna(subset=['data', 'chuva_mm'])
    
    # Adicionar metadados
    df_longo['estacao'] = metadata.get('nome_posto', 'AGUA BRANCA')
    df_longo['municipio'] = metadata.get('municipio', 'SAO PAULO')
    
    # Converter coordenadas DMS → Decimal
    lat_str = metadata.get('LATITUDE', '').replace(';', '')
    lon_str = metadata.get('LONGITUDE', '').replace(';', '')
    
    lat_decimal = converter_coordenadas(lat_str)
    lon_decimal = converter_coordenadas(lon_str)
    
    df_longo['latitude'] = lat_decimal * -1 if lat_decimal else -23.5  # Sul (negativo), default SP
    df_longo['longitude'] = lon_decimal * -1 if lon_decimal else -46.6  # Oeste (negativo), default SP
    
    return df_longo


def agregar_chuva_diaria(df):
    """
    Agrega dados de chuva por dia.
    
    Args:
        df: DataFrame com dados de chuva
        
    Returns:
        DataFrame agregado por dia
    """
    if 'data' not in df.columns:
        return df
    
    # Encontrar coluna com valores de chuva
    col_chuva = None
    for col in df.columns:
        if 'chuva' in col.lower() or 'mm' in col.lower() or 'precipitacao' in col.lower():
            col_chuva = col
            break
    
    if col_chuva is None:
        # Se não encontrar, usar a primeira coluna numérica
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            col_chuva = numeric_cols[0]
    
    if col_chuva:
        df_agg = df.groupby('data').agg({
            col_chuva: ['sum', 'mean', 'max'],
            'estacao': 'first',
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        
        df_agg.columns = ['data', 'chuva_total', 'chuva_media', 'chuva_maxima', 'estacao', 'latitude', 'longitude']
        return df_agg
    
    return df


def classificar_intensidade_chuva(chuva_mm):
    """
    Classifica a intensidade da chuva.
    
    Args:
        chuva_mm: Quantidade de chuva em mm
        
    Returns:
        Classificação (Seco, Fraca, Moderada, Forte, Muito Forte)
    """
    if pd.isna(chuva_mm) or chuva_mm == 0:
        return 'Seco'
    elif chuva_mm < 5:
        return 'Fraca'
    elif chuva_mm < 25:
        return 'Moderada'
    elif chuva_mm < 50:
        return 'Forte'
    else:
        return 'Muito Forte'


def processar_dados_chuva_completo(filepath):
    """
    Pipeline completo de processamento de dados de chuva.
    
    Args:
        filepath: Caminho para o arquivo CSV
        
    Returns:
        DataFrame processado e pronto para análise
    """
    # Processar arquivo
    df = processar_arquivo_chuva(filepath)
    
    # Agregar por dia
    df_agg = agregar_chuva_diaria(df)
    
    # Classificar intensidade
    if 'chuva_total' in df_agg.columns:
        df_agg['intensidade'] = df_agg['chuva_total'].apply(classificar_intensidade_chuva)
    
    # Adicionar features temporais
    if 'data' in df_agg.columns:
        df_agg['ano'] = df_agg['data'].dt.year
        df_agg['mes'] = df_agg['data'].dt.month
        df_agg['dia_semana'] = df_agg['data'].dt.dayofweek
        df_agg['trimestre'] = df_agg['data'].dt.quarter
    
    return df_agg


if __name__ == '__main__':
    # Teste do módulo
    df = processar_dados_chuva_completo('data/chuva_sp.csv')
    print(df.head())
    print(f"\nShape: {df.shape}")
    print(f"\nColunas: {df.columns.tolist()}")
