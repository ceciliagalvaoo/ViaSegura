"""
Módulo para processamento de dados de acidentes de trânsito.
"""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def processar_acidentes_kmz(kmz_path):
    """
    Processa arquivo KMZ de acidentes de trânsito extraindo dados do KML.
    
    Args:
        kmz_path: Caminho para o arquivo KMZ
        
    Returns:
        GeoDataFrame com dados de acidentes
    """
    print("Descompactando KMZ...")
    # Descompactar KMZ e ler KML
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_content = zf.read('doc.kml').decode('utf-8')
    
    print("Parseando XML...")
    # Parsear XML
    root = ET.fromstring(kml_content)
    
    # Namespace do KML
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Listas para armazenar dados
    acidentes = []
    
    print("Extraindo placemarks (pode demorar - arquivo grande)...")
    # Iterar sobre Placemarks
    count = 0
    for placemark in root.findall('.//kml:Placemark', ns):
        try:
            # Extrair coordenadas
            coords_elem = placemark.find('.//kml:coordinates', ns)
            if coords_elem is None:
                continue
            
            coords_text = coords_elem.text.strip()
            lon, lat, alt = coords_text.split(',')
            
            # Extrair atributos (SimpleData)
            atributos = {
                'longitude': float(lon),
                'latitude': float(lat)
            }
            
            for simple_data in placemark.findall('.//kml:SimpleData', ns):
                nome = simple_data.get('name')
                valor = simple_data.text
                atributos[nome] = valor
            
            acidentes.append(atributos)
            
            count += 1
            if count % 10000 == 0:
                print(f"  Processados: {count:,} registros...")
        
        except Exception as e:
            # Pular placemarks com erros
            continue
    
    print(f"Total extraído: {len(acidentes):,} acidentes")
    
    # Criar DataFrame
    df = pd.DataFrame(acidentes)
    
    # Converter campos numéricos
    campos_numericos = ['aci_id', 'aci_altnum', 'aci_auto', 'aci_bicicl', 
                       'aci_caminh', 'aci_fatais', 'aci_ferido', 'aci_moto']
    
    for campo in campos_numericos:
        if campo in df.columns:
            df[campo] = pd.to_numeric(df[campo], errors='coerce').fillna(0).astype(int)
    
    # Converter data (formato: YYYYMMDD)
    if 'aci_data' in df.columns:
        df['data'] = pd.to_datetime(df['aci_data'], format='%Y%m%d', errors='coerce')
    
    # Criar GeoDataFrame
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
    
    return gdf


def filtrar_acidentes_poste(gdf):
    """
    Filtra acidentes que provavelmente envolveram colisão com objetos fixos (postes).
    
    Critérios:
    1. aci_outros == 1 (indicador de objeto/outro)
    2. OU: Nenhum veículo envolvido (auto=0, moto=0, bicicl=0, caminh=0, onibus=0)
       → Provável colisão com objeto fixo
    
    Args:
        gdf: GeoDataFrame com dados de acidentes
        
    Returns:
        GeoDataFrame filtrado
    """
    # Garantir que campos existem
    campos_veiculo = ['aci_auto', 'aci_moto', 'aci_bicicl', 'aci_caminh']
    for campo in campos_veiculo:
        if campo not in gdf.columns:
            gdf[campo] = 0
    
    if 'aci_outros' not in gdf.columns:
        gdf['aci_outros'] = '0'
    
    # Converter aci_onibus para numérico (pode ser string)
    if 'aci_onibus' in gdf.columns:
        gdf['aci_onibus_num'] = pd.to_numeric(gdf['aci_onibus'], errors='coerce').fillna(0).astype(int)
    else:
        gdf['aci_onibus_num'] = 0
    
    # Filtro 1: aci_outros == 1
    filtro_outros = (gdf['aci_outros'].astype(str) == '1')
    
    # Filtro 2: Nenhum veículo envolvido
    filtro_sem_veiculos = (
        (gdf['aci_auto'] == 0) & 
        (gdf['aci_moto'] == 0) & 
        (gdf['aci_bicicl'] == 0) & 
        (gdf['aci_caminh'] == 0) &
        (gdf['aci_onibus_num'] == 0)
    )
    
    # Combinar filtros (OU lógico)
    gdf_filtrado = gdf[filtro_outros | filtro_sem_veiculos].copy()
    
    print(f"Total de acidentes: {len(gdf)}")
    print(f"Acidentes com objetos fixos (possível poste): {len(gdf_filtrado)}")
    print(f"  - Por aci_outros=1: {filtro_outros.sum()}")
    print(f"  - Por ausência de veículos: {filtro_sem_veiculos.sum()}")
    
    return gdf_filtrado
    
    # Combinar filtros (OU lógico)
    gdf_filtrado = gdf[filtro_outros | filtro_sem_veiculos].copy()
    
    print(f"Total de acidentes: {len(gdf)}")
    print(f"Acidentes com objetos fixos (possível poste): {len(gdf_filtrado)}")
    print(f"  - Por aci_outros=1: {filtro_outros.sum()}")
    print(f"  - Por ausência de veículos: {filtro_sem_veiculos.sum()}")
    
    return gdf_filtrado


def agregar_acidentes_espacial(gdf, cell_size=0.01):
    """
    Agrega acidentes espacialmente em uma grade regular.
    Filtra acidentes que envolvem colisão com objeto fixo (poste, muro, etc.).
    
    Args:
        gdf: GeoDataFrame com dados de acidentes
        
    Returns:
        GeoDataFrame filtrado
    """
    if gdf is None or gdf.empty:
        return gdf
    
    # Palavras-chave para identificar colisões com objetos fixos
    palavras_chave = ['poste', 'objeto fixo', 'objeto', 'muro', 'árvore', 
                      'coluna', 'pilar', 'rede elétrica', 'cabo', 'fiação']
    
    # Procurar nas colunas de descrição/tipo
    mask = pd.Series([False] * len(gdf))
    
    for col in gdf.columns:
        if gdf[col].dtype == 'object':
            for palavra in palavras_chave:
                mask |= gdf[col].astype(str).str.contains(palavra, case=False, na=False)
    
    gdf_filtrado = gdf[mask].copy()
    
    return gdf_filtrado


def extrair_coordenadas(gdf):
    """
    Extrai coordenadas latitude e longitude do GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame
        
    Returns:
        GeoDataFrame com colunas latitude e longitude
    """
    if 'geometry' in gdf.columns:
        gdf['longitude'] = gdf.geometry.x
        gdf['latitude'] = gdf.geometry.y
    
    return gdf


def agregar_acidentes_espacial(gdf, grid_size=0.01):
    """
    Agrega acidentes em uma grade espacial.
    
    Args:
        gdf: GeoDataFrame com acidentes
        grid_size: Tamanho da célula da grade em graus (aprox. 1km = 0.01 graus)
        
    Returns:
        GeoDataFrame agregado por célula
    """
    if gdf is None or gdf.empty:
        return gdf
    
    # Criar grid
    gdf['grid_x'] = (gdf['longitude'] / grid_size).round() * grid_size
    gdf['grid_y'] = (gdf['latitude'] / grid_size).round() * grid_size
    
    # Agregar por grid
    agg_dict = {
        'longitude': 'mean',
        'latitude': 'mean'
    }
    
    # Adicionar outras colunas numéricas
    numeric_cols = gdf.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if col not in ['longitude', 'latitude', 'grid_x', 'grid_y']:
            agg_dict[col] = 'sum'
    
    df_agg = gdf.groupby(['grid_x', 'grid_y']).agg(agg_dict).reset_index()
    df_agg['num_acidentes'] = gdf.groupby(['grid_x', 'grid_y']).size().values
    
    # Converter de volta para GeoDataFrame
    geometry = [Point(xy) for xy in zip(df_agg['longitude'], df_agg['latitude'])]
    gdf_agg = gpd.GeoDataFrame(df_agg, geometry=geometry, crs='EPSG:4326')
    
    return gdf_agg


def processar_dados_acidentes_completo(kmz_path, filtrar_objetos_fixos=True):
    """
    Pipeline completo de processamento de dados de acidentes.
    
    Args:
        kmz_path: Caminho para o arquivo KMZ
        filtrar_objetos_fixos: Se True, filtra apenas acidentes com objetos fixos
        
    Returns:
        GeoDataFrame processado
    """
    # Processar KMZ
    gdf = processar_acidentes_kmz(kmz_path)
    
    if gdf is None or gdf.empty:
        print("Não foi possível processar o arquivo de acidentes.")
        return None
    
    # Extrair coordenadas
    gdf = extrair_coordenadas(gdf)
    
    # Filtrar acidentes com objetos fixos
    if filtrar_objetos_fixos:
        gdf = filtrar_acidentes_poste(gdf)
    
    # Agregar espacialmente
    gdf_agg = agregar_acidentes_espacial(gdf)
    
    return gdf_agg


if __name__ == '__main__':
    # Teste do módulo
    gdf = processar_dados_acidentes_completo('data/acidente_transito.kmz')
    if gdf is not None:
        print(gdf.head())
        print(f"\nShape: {gdf.shape}")
        print(f"\nColunas: {gdf.columns.tolist()}")
