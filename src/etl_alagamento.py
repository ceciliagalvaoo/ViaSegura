"""
Módulo para processamento de dados de alagamento (Shapefiles).
"""
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.geometry import Point


def listar_shapefiles_alagamento(data_dir='data/alagamento'):
    """
    Lista todos os shapefiles de alagamento disponíveis.
    
    Args:
        data_dir: Diretório contendo os shapefiles
        
    Returns:
        Lista de caminhos para os shapefiles
    """
    data_path = Path(data_dir)
    shapefiles = list(data_path.glob('*.shp'))
    return sorted(shapefiles)


def extrair_ano_shapefile(filepath):
    """
    Extrai o ano do nome do arquivo shapefile.
    
    Args:
        filepath: Caminho para o shapefile
        
    Returns:
        Ano (int) ou None
    """
    import re
    filename = Path(filepath).stem
    match = re.search(r'(\d{4})', filename)
    if match:
        return int(match.group(1))
    return None


def processar_shapefile_alagamento(shapefile_path):
    """
    Processa um shapefile de alagamento.
    
    Args:
        shapefile_path: Caminho para o shapefile
        
    Returns:
        GeoDataFrame com dados de alagamento processados
    """
    try:
        gdf = gpd.read_file(shapefile_path, encoding='utf-8')
        
        # Adicionar ano do arquivo
        ano = extrair_ano_shapefile(shapefile_path)
        if ano:
            gdf['ano'] = ano
        
        # SIRGAS 2000 (provável: EPSG:31983 - UTM Zone 23S)
        # Converter para WGS84 (EPSG:4326) para mapas web
        if gdf.crs is None:
            print(f"AVISO: CRS não definido em {shapefile_path.name}, assumindo EPSG:31983")
            gdf.set_crs('EPSG:31983', inplace=True)
        
        if gdf.crs.to_string() != 'EPSG:4326':
            print(f"Convertendo {shapefile_path.name} de {gdf.crs} para EPSG:4326")
            gdf = gdf.to_crs('EPSG:4326')
        
        # Extrair centroides (se forem polígonos)
        if gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
            gdf['latitude'] = gdf.geometry.centroid.y
            gdf['longitude'] = gdf.geometry.centroid.x
        else:
            gdf['latitude'] = gdf.geometry.y
            gdf['longitude'] = gdf.geometry.x
        
        print(f"✓ Processado: {shapefile_path.name} - {len(gdf)} registros")
        
        return gdf
    
    except Exception as e:
        print(f"✗ Erro ao processar {shapefile_path}: {e}")
        return None


def processar_todos_shapefiles(data_dir='data/alagamento'):
    """
    Processa todos os shapefiles de alagamento e combina em um único GeoDataFrame.
    
    Args:
        data_dir: Diretório contendo os shapefiles
        
    Returns:
        GeoDataFrame combinado
    """
    shapefiles = listar_shapefiles_alagamento(data_dir)
    
    if not shapefiles:
        print(f"Nenhum shapefile encontrado em {data_dir}")
        return None
    
    gdfs = []
    
    for shapefile in shapefiles:
        print(f"Processando: {shapefile.name}")
        gdf = processar_shapefile_alagamento(shapefile)
        if gdf is not None and not gdf.empty:
            gdfs.append(gdf)
    
    if not gdfs:
        return None
    
    # Combinar todos os GeoDataFrames
    gdf_combined = pd.concat(gdfs, ignore_index=True)
    
    return gdf_combined


def classificar_risco_alagamento(gdf):
    """
    Classifica o risco de alagamento com base nas colunas disponíveis.
    
    Args:
        gdf: GeoDataFrame com dados de alagamento
        
    Returns:
        GeoDataFrame com coluna de classificação de risco
    """
    if gdf is None or gdf.empty:
        return gdf
    
    # Procurar coluna de risco
    colunas_risco = [col for col in gdf.columns if 'risco' in col.lower() or 'risk' in col.lower()]
    
    if colunas_risco:
        col_risco = colunas_risco[0]
        
        # Normalizar classificação
        def normalizar_risco(valor):
            valor_str = str(valor).lower()
            if any(x in valor_str for x in ['alto', 'high', 'elevado', 'a']):
                return 'Alto'
            elif any(x in valor_str for x in ['médio', 'medio', 'medium', 'm']):
                return 'Médio'
            elif any(x in valor_str for x in ['baixo', 'low', 'b']):
                return 'Baixo'
            return 'Não Classificado'
        
        gdf['risco_normalizado'] = gdf[col_risco].apply(normalizar_risco)
    else:
        gdf['risco_normalizado'] = 'Não Classificado'
    
    return gdf


def extrair_centroides(gdf):
    """
    Extrai os centroides das geometrias e adiciona como colunas lat/lon.
    
    Args:
        gdf: GeoDataFrame
        
    Returns:
        GeoDataFrame com colunas latitude e longitude
    """
    if 'geometry' in gdf.columns:
        centroides = gdf.geometry.centroid
        gdf['longitude'] = centroides.x
        gdf['latitude'] = centroides.y
    
    return gdf


def agregar_alagamento_espacial(gdf, grid_size=0.01):
    """
    Agrega dados de alagamento em uma grade espacial.
    
    Args:
        gdf: GeoDataFrame com alagamentos
        grid_size: Tamanho da célula da grade em graus
        
    Returns:
        GeoDataFrame agregado
    """
    if gdf is None or gdf.empty:
        return gdf
    
    # Extrair centroides se necessário
    if 'longitude' not in gdf.columns:
        gdf = extrair_centroides(gdf)
    
    # Criar grid
    gdf['grid_x'] = (gdf['longitude'] / grid_size).round() * grid_size
    gdf['grid_y'] = (gdf['latitude'] / grid_size).round() * grid_size
    
    # Agregar
    agg_dict = {
        'longitude': 'mean',
        'latitude': 'mean',
        'ano': 'first'
    }
    
    if 'risco_normalizado' in gdf.columns:
        # Contar ocorrências por nível de risco
        df_agg = gdf.groupby(['grid_x', 'grid_y', 'risco_normalizado']).size().reset_index(name='count')
        df_pivot = df_agg.pivot_table(index=['grid_x', 'grid_y'], 
                                      columns='risco_normalizado', 
                                      values='count', 
                                      fill_value=0).reset_index()
        
        # Adicionar coordenadas médias
        coords = gdf.groupby(['grid_x', 'grid_y'])[['longitude', 'latitude']].mean().reset_index()
        df_pivot = df_pivot.merge(coords, on=['grid_x', 'grid_y'])
        
        # Total de ocorrências
        df_pivot['total_ocorrencias'] = df_pivot.select_dtypes(include=['number']).drop(['grid_x', 'grid_y', 'longitude', 'latitude'], axis=1, errors='ignore').sum(axis=1)
        
        # Converter para GeoDataFrame
        geometry = [Point(xy) for xy in zip(df_pivot['longitude'], df_pivot['latitude'])]
        gdf_agg = gpd.GeoDataFrame(df_pivot, geometry=geometry, crs='EPSG:4326')
        
        return gdf_agg
    else:
        df_agg = gdf.groupby(['grid_x', 'grid_y']).agg(agg_dict).reset_index()
        df_agg['num_ocorrencias'] = gdf.groupby(['grid_x', 'grid_y']).size().values
        
        geometry = [Point(xy) for xy in zip(df_agg['longitude'], df_agg['latitude'])]
        gdf_agg = gpd.GeoDataFrame(df_agg, geometry=geometry, crs='EPSG:4326')
        
        return gdf_agg


def processar_dados_alagamento_completo(data_dir='data/alagamento'):
    """
    Pipeline completo de processamento de dados de alagamento.
    
    Args:
        data_dir: Diretório contendo os shapefiles
        
    Returns:
        GeoDataFrame processado
    """
    # Processar todos os shapefiles
    gdf = processar_todos_shapefiles(data_dir)
    
    if gdf is None or gdf.empty:
        print("Não foi possível processar os dados de alagamento.")
        return None
    
    # Classificar risco
    gdf = classificar_risco_alagamento(gdf)
    
    # Extrair centroides
    gdf = extrair_centroides(gdf)
    
    # Agregar espacialmente
    gdf_agg = agregar_alagamento_espacial(gdf)
    
    return gdf_agg


if __name__ == '__main__':
    # Teste do módulo
    gdf = processar_dados_alagamento_completo()
    if gdf is not None:
        print(gdf.head())
        print(f"\nShape: {gdf.shape}")
        print(f"\nColunas: {gdf.columns.tolist()}")
        if 'risco_normalizado' in gdf.columns:
            print(f"\nDistribuição de risco:")
            print(gdf['risco_normalizado'].value_counts())
