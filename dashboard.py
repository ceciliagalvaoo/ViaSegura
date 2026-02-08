"""
Dashboard Energisa ViaSegura - Versão focada em Soluções
Sistema de mapa preditivo de risco para acidentes com a rede elétrica
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / 'src'))

from etl_chuva import processar_arquivo_chuva
from etl_acidentes import processar_acidentes_kmz, filtrar_acidentes_poste
from etl_alagamento import processar_todos_shapefiles
from modelo_risco import ModeloRiscoViaSegura
from analise_temporal import (
    classificar_areas_por_risco, 
    gerar_recomendacoes,
    analisar_sazonalidade
)

# Configuração da página
st.set_page_config(
    page_title="Energisa ViaSegura",
    page_icon="⚡",
    layout="wide"
)

# Estilos customizados
st.markdown("""
<style>
    .risk-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .risk-baixo { background-color: #e8f8f5; border-left: 5px solid #25aae2; }
    .risk-medio { background-color: #fdfde8; border-left: 5px solid #c3cc25; }
    .risk-alto { background-color: #f8d7da; border-left: 5px solid #dc3545; }
    
    .metric-card {
        background: linear-gradient(135deg, #25aae2 0%, #1a8ab8 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    
    .main-header {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Cabeçalho
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("img/Icone.svg", width=150)

with col_title:
    st.markdown("# Energisa ViaSegura - Soluções para Minimizar Riscos")
    st.markdown("### Como podemos garantir maior segurança da população próxima à rede elétrica?")

st.markdown("---")

# Cache para dados
@st.cache_data(show_spinner="Processando dados de 1937 a 2025...")
def carregar_dados():
    """Carrega todos os dados necessários."""
    import os
    
    df_chuva = processar_arquivo_chuva('data/chuva_sp.csv')
    
    # Verificar se arquivo de acidentes existe
    if os.path.exists('data/acidente_transito.kmz'):
        try:
            gdf_acidentes_todos = processar_acidentes_kmz('data/acidente_transito.kmz')
            gdf_acidentes = filtrar_acidentes_poste(gdf_acidentes_todos)
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar arquivo: {str(e)}. Usando modo demonstração.")
            gdf_acidentes = criar_dados_demo_acidentes()
    else:
        # Modo demo com proporções realistas de risco
        st.info("ℹ️ **Modo Demonstração:** Usando dados sintéticos (arquivo completo: 326MB, 192.850 acidentes)")
        gdf_acidentes = criar_dados_demo_acidentes()
    
    gdf_alagamento = processar_todos_shapefiles('data/alagamento')
    
    return df_chuva, gdf_acidentes, gdf_alagamento

def criar_dados_demo_acidentes():
    """Cria dados sintéticos respeitando proporções de índice de risco."""
    import geopandas as gpd
    from shapely.geometry import Point
    import numpy as np
    
    np.random.seed(42)
    
    # Criar 3 clusters de ALTO RISCO (densidade muito alta - 50+ eventos/área)
    high_risk_clusters = [
        (-23.547, -46.634, 1500),  # Região da Paulista (CRÍTICA)
        (-23.533, -46.625, 1200),  # Centro histórico (CRÍTICA)
        (-23.575, -46.648, 1000),  # Marginal Tietê (CRÍTICA)
    ]
    
    high_risk_points = []
    for lat, lon, n_points in high_risk_clusters:
        # Cluster MUITO concentrado (raio ~500m) para índice alto
        lats = np.random.normal(lat, 0.005, n_points)
        lons = np.random.normal(lon, 0.005, n_points)
        high_risk_points.extend(list(zip(lats, lons)))
    
    # Criar 5 clusters de MÉDIO RISCO (densidade média - 15-50 eventos/área)
    medium_risk_clusters = [
        (-23.560, -46.660, 800),   # Zona Oeste
        (-23.590, -46.640, 700),   # Zona Sul
        (-23.520, -46.615, 600),   # Zona Norte
        (-23.565, -46.625, 600),   # Centro expandido
        (-23.545, -46.670, 500),   # Vila Madalena
    ]
    
    medium_risk_points = []
    for lat, lon, n_points in medium_risk_clusters:
        # Cluster moderadamente disperso (raio ~1.5km)
        lats = np.random.normal(lat, 0.015, n_points)
        lons = np.random.normal(lon, 0.015, n_points)
        medium_risk_points.extend(list(zip(lats, lons)))
    
    # Criar BAIXO RISCO (disperso pela cidade - <15 eventos/área)
    n_low_risk = 2000
    lats_low = np.random.uniform(-23.80, -23.40, n_low_risk)
    lons_low = np.random.uniform(-46.75, -46.45, n_low_risk)
    low_risk_points = list(zip(lats_low, lons_low))
    
    # Combinar: ~40% alto risco, ~35% médio, ~25% baixo
    all_points = high_risk_points + medium_risk_points + low_risk_points
    n_total = len(all_points)
    
    lats = [p[0] for p in all_points]
    lons = [p[1] for p in all_points]
    
    # Limitar aos bounds reais de SP
    lats = np.clip(lats, -23.99, -23.36)
    lons = np.clip(lons, -46.82, -46.37)
    
    # Datas distribuídas ao longo do período
    dates = pd.date_range('2013-01-01', '2025-01-31', periods=n_total)
    
    return gpd.GeoDataFrame({
        'latitude': lats,
        'longitude': lons,
        'data': dates,
        'geometry': [Point(lon, lat) for lon, lat in zip(lons, lats)]
    }, crs='EPSG:4326')

@st.cache_data
def obter_endereco(lat, lon):
    """Converte coordenadas em endereço usando geocoding reverso."""
    try:
        geolocator = Nominatim(user_agent="energisa_viasegura")
        location = geolocator.reverse(f"{lat}, {lon}", timeout=10, language='pt')
        
        if location and location.raw:
            addr = location.raw.get('address', {})
            
            # Tentar construir endereço estruturado
            partes = []
            
            # Rua/Avenida
            rua = addr.get('road') or addr.get('street') or addr.get('pedestrian')
            if rua:
                partes.append(rua)
            
            # Bairro
            bairro = addr.get('suburb') or addr.get('neighbourhood') or addr.get('city_district')
            if bairro and bairro != 'São Paulo':
                partes.append(bairro)
            elif not partes:  # Se não tem rua nem bairro, pelo menos mostrar cidade
                cidade = addr.get('city') or addr.get('municipality') or 'São Paulo'
                partes.append(cidade)
            
            if partes:
                return ', '.join(partes)
        
        # Fallback para coordenadas
        return f"Lat: {lat:.4f}, Lon: {lon:.4f}"
    except (GeocoderTimedOut, GeocoderServiceError, Exception):
        return f"Lat: {lat:.4f}, Lon: {lon:.4f}"

@st.cache_data
def calcular_modelo(_df_chuva, _gdf_acidentes, _gdf_alagamento, 
                    peso_acidentes, peso_alagamento, peso_chuva, grid_size):
    """Calcula modelo de risco."""
    pesos = {
        'acidentes': peso_acidentes,
        'alagamento': peso_alagamento,
        'chuva': peso_chuva
    }
    
    modelo = ModeloRiscoViaSegura(pesos=pesos)
    
    # Determinar bounds da cidade com base nos dados
    bounds = (
        min(_gdf_acidentes.geometry.x.min(), _gdf_alagamento.geometry.x.min()) - 0.05,
        min(_gdf_acidentes.geometry.y.min(), _gdf_alagamento.geometry.y.min()) - 0.05,
        max(_gdf_acidentes.geometry.x.max(), _gdf_alagamento.geometry.x.max()) + 0.05,
        max(_gdf_acidentes.geometry.y.max(), _gdf_alagamento.geometry.y.max()) + 0.05
    )
    
    # Criar grid
    gdf_grid = modelo.criar_grid_cidade(bounds, grid_size=grid_size)
    
    # Calcular scores
    score_acidentes = modelo.calcular_score_acidentes(gdf_grid, _gdf_acidentes)
    score_alagamento = modelo.calcular_score_alagamento(gdf_grid, _gdf_alagamento)
    score_chuva = modelo.calcular_score_chuva('Moderada')  # Converter para numérico
    
    # Calcular índice de risco
    grid_risco = modelo.calcular_indice_risco(
        score_acidentes, 
        score_alagamento,
        score_chuva=score_chuva,
        gdf_grid=gdf_grid
    )
    
    return grid_risco, modelo

# Sidebar
st.sidebar.header("Configurações do Modelo")

with st.sidebar:
    st.subheader("Pesos do Modelo de Risco")
    peso_acidentes = st.slider("Acidentes", 0.0, 1.0, 0.4, 0.05)
    peso_alagamento = st.slider("Alagamento", 0.0, 1.0, 0.3, 0.05)
    peso_chuva = st.slider("Chuva", 0.0, 1.0, 0.3, 0.05)
    
    total_peso = peso_acidentes + peso_alagamento + peso_chuva
    if abs(total_peso - 1.0) > 0.01:
        st.warning(f"⚠️ Soma dos pesos: {total_peso:.2f} (ideal: 1.0)")
    
    st.markdown("---")
    st.subheader("Grade de Análise")
    grid_size = st.selectbox(
        "Resolução da grade",
        options=[0.01, 0.02, 0.03, 0.05],
        index=1,
        format_func=lambda x: f"~{x*111:.1f} km/célula"
    )
    
    st.markdown("---")
    st.subheader("Filtros de Visualização")
    mostrar_niveis = st.multiselect(
        "Níveis de risco",
        options=['baixo', 'medio', 'alto'],
        default=['medio', 'alto']
    )
    
    if st.button("Recalcular", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Carregar dados
try:
    df_chuva, gdf_acidentes, gdf_alagamento = carregar_dados()
    
    # Calcular modelo
    grid_risco, modelo = calcular_modelo(
        df_chuva, gdf_acidentes, gdf_alagamento,
        peso_acidentes, peso_alagamento, peso_chuva, grid_size
    )
    
    # Classificar áreas
    grid_classificado = classificar_areas_por_risco(grid_risco)
    
    # Estatísticas de cobertura
    distribuicao = grid_classificado['categoria_risco'].value_counts()
    total_areas = len(grid_classificado)
    
    # ========== TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Visão Executiva",
        "Mapa de Riscos",
        "Análise por Níveis", 
        "Tendências Temporais",
        "Modelo Preditivo",
        "Recomendações"
    ])
    
    # ========== TAB 1: VISÃO EXECUTIVA ==========
    with tab1:
        st.header("Visão Executiva - Panorama de Riscos")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            n_alto = distribuicao.get('alto', 0)
            perc_alto = (n_alto / total_areas * 100) if total_areas > 0 else 0
            st.metric(
                "Áreas CRÍTICAS",
                f"{n_alto}",
                delta=f"{perc_alto:.1f}% do total",
                delta_color="inverse"
            )
        
        with col2:
            n_medio = distribuicao.get('medio', 0)
            perc_medio = (n_medio / total_areas * 100) if total_areas > 0 else 0
            st.metric(
                "Áreas de ATENÇÃO",
                f"{n_medio}",
                delta=f"{perc_medio:.1f}% do total",
                delta_color="normal"
            )
        
        with col3:
            n_baixo = distribuicao.get('baixo', 0)
            perc_baixo = (n_baixo / total_areas * 100) if total_areas > 0 else 0
            st.metric(
                "Áreas SEGURAS",
                f"{n_baixo}",
                delta=f"{perc_baixo:.1f}% do total"
            )
        
        with col4:
            st.metric(
                "Total de Áreas",
                f"{total_areas}",
                delta=f"Grade {grid_size}"
            )
        
        st.markdown("---")
        
        # Gráfico de distribuição
        col_chart, col_info = st.columns([2, 1])
        
        with col_chart:
            st.subheader("Distribuição de Risco na Cidade")
            
            cores = {'baixo': '#25aae2', 'medio': '#c3cc25', 'alto': '#dc3545'}
            fig = go.Figure(data=[go.Pie(
                labels=[k.upper() for k in distribuicao.index],
                values=distribuicao.values,
                marker=dict(colors=[cores.get(k, '#999') for k in distribuicao.index]),
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>%{value} áreas<br>%{percent}<extra></extra>'
            )])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_info:
            st.subheader("Resumo dos Dados")
            st.markdown(f"""
            **Período analisado:** 2013-2025
            
            **Fontes de dados:**
            - Chuva: {len(df_chuva):,} registros
            - Acidentes: {len(gdf_acidentes):,} eventos
            - Alagamento: {len(gdf_alagamento):,} pontos
            
            **Pesos aplicados:**
            - Acidentes: {peso_acidentes*100:.0f}%
            - Alagamento: {peso_alagamento*100:.0f}%
            - Chuva: {peso_chuva*100:.0f}%
            """)
        
        # Últimos Alertas
        st.markdown("---")
        st.subheader("Últimos Alertas de Perigo")
        
        # Preparar dados de alertas
        alertas = []
        
        # Alertas de acidentes (2 alertas de 1º de fevereiro de 2025)
        if 'data' in gdf_acidentes.columns:
            # Converter data para datetime se necessário
            gdf_acidentes_temp = gdf_acidentes.copy()
            gdf_acidentes_temp['data'] = pd.to_datetime(gdf_acidentes_temp['data'], errors='coerce')
            # Filtrar acidentes de 1º de fevereiro de 2025
            data_alvo = pd.Timestamp('2025-02-01')
            acidentes_data_especifica = gdf_acidentes_temp[gdf_acidentes_temp['data'] == data_alvo].dropna(subset=['data'])
            if len(acidentes_data_especifica) >= 2:
                acidentes_recentes = acidentes_data_especifica.head(2)[['data', 'latitude', 'longitude']].copy()
            else:
                # Fallback caso não tenha 2 acidentes nessa data específica
                acidentes_recentes = gdf_acidentes_temp.dropna(subset=['data']).sort_values('data', ascending=False).head(2)[['data', 'latitude', 'longitude']].copy()
            
            for idx, row in acidentes_recentes.iterrows():
                # Determinar risco baseado na densidade local
                ponto = (row['latitude'], row['longitude'])
                acidentes_proximos = gdf_acidentes[
                    (abs(gdf_acidentes.geometry.y - ponto[0]) < 0.01) & 
                    (abs(gdf_acidentes.geometry.x - ponto[1]) < 0.01)
                ]
                n_proximos = len(acidentes_proximos)
                
                if n_proximos > 50:
                    nivel = 'alto'
                elif n_proximos > 20:
                    nivel = 'medio'
                else:
                    nivel = 'baixo'
                
                alertas.append({
                    'data': row['data'],
                    'tipo': 'Acidente',
                    'nivel': nivel,
                    'motivo': f'{n_proximos} acidentes próximos (área crítica)' if n_proximos > 50 else f'{n_proximos} acidentes na região',
                    'localizacao': obter_endereco(ponto[0], ponto[1])
                })
        
        # Alertas de alagamento (últimos 10 pontos por ano mais recente)
        if 'ano' in gdf_alagamento.columns:
            # Usar ano em vez de data para evitar problemas de tipo
            alag_recentes = gdf_alagamento.sort_values('ano', ascending=False).head(10)[['data', 'latitude', 'longitude']].copy()
            for idx, row in alag_recentes.iterrows():
                ponto = (row['latitude'], row['longitude'])
                alag_proximos = gdf_alagamento[
                    (abs(gdf_alagamento.geometry.y - ponto[0]) < 0.005) & 
                    (abs(gdf_alagamento.geometry.x - ponto[1]) < 0.005)
                ]
                n_proximos = len(alag_proximos)
                
                if n_proximos > 10:
                    nivel = 'alto'
                elif n_proximos > 5:
                    nivel = 'medio'
                else:
                    nivel = 'baixo'
                
                alertas.append({
                    'data': row['data'],
                    'tipo': 'Alagamento',
                    'nivel': nivel,
                    'motivo': f'Histórico de {n_proximos} ocorrências nesta área',
                    'localizacao': obter_endereco(ponto[0], ponto[1])
                })
        
        # Alertas de chuva intensa (últimos 10 dias com mais de 50mm)
        if 'data' in df_chuva.columns and 'chuva_mm' in df_chuva.columns:
            # Converter data para datetime
            df_chuva_temp = df_chuva.copy()
            df_chuva_temp['data'] = pd.to_datetime(df_chuva_temp['data'], errors='coerce')
            chuvas_intensas = df_chuva_temp[df_chuva_temp['chuva_mm'] > 50].dropna(subset=['data']).sort_values('data', ascending=False).head(10)[['data', 'chuva_mm']].copy()
            
            for idx, row in chuvas_intensas.iterrows():
                chuva = row['chuva_mm']
                
                if chuva > 100:
                    nivel = 'alto'
                elif chuva > 75:
                    nivel = 'medio'
                else:
                    nivel = 'baixo'
                
                alertas.append({
                    'data': row['data'],
                    'tipo': 'Chuva Intensa',
                    'nivel': nivel,
                    'motivo': f'Precipitação de {chuva:.1f}mm (risco de danos à rede)',
                    'localizacao': 'Toda cidade (Estação Mirante de Santana)'
                })
        
        # Ordenar alertas por data (mais recentes primeiro)
        if alertas:
            df_alertas = pd.DataFrame(alertas).sort_values('data', ascending=False).head(15)
            
            # Exibir alertas em cards
            for i in range(0, len(df_alertas), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(df_alertas):
                        alerta = df_alertas.iloc[i + j]
                        
                        # Cores por nível
                        cor_map = {
                            'alto': ('#f8d7da', '#dc3545', '#721c24'),
                            'medio': ('#fdfde8', '#c3cc25', '#6b6d14'),
                            'baixo': ('#e8f8f5', '#25aae2', '#1a5d7a')
                        }
                        bg_color, border_color, text_color = cor_map[alerta['nivel']]
                        
                        with col:
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; border-left: 5px solid {border_color}; 
                                        padding: 15px; border-radius: 5px; margin-bottom: 10px; min-height: 180px;">
                                <h4 style="color: {text_color}; margin: 0 0 10px 0;">
                                    {alerta['tipo']} - RISCO {alerta['nivel'].upper()}
                                </h4>
                                <p style="margin: 5px 0; font-size: 0.9em;">
                                    <strong>📅 Data:</strong> {alerta['data'].strftime('%d/%m/%Y')}
                                </p>
                                <p style="margin: 5px 0; font-size: 0.85em;">
                                    <strong>📍 Local:</strong> {alerta['localizacao']}
                                </p>
                                <p style="margin: 10px 0 0 0; font-size: 0.85em; font-style: italic;">
                                    {alerta['motivo']}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("Nenhum alerta recente registrado.")
        
        # Simulador de Alerta por Email
        st.markdown("---")
        st.subheader("Simulador de Alerta por Email")
        
        col_email1, col_email2 = st.columns([1, 1])
        
        with col_email1:
            st.markdown("**Cadastre-se para receber alertas**")
            st.info("📅 Data da simulação: 1º de fevereiro de 2025")
            email_usuario = st.text_input("Email", placeholder="seu.email@exemplo.com")
            endereco_usuario = st.text_input("Endereço", placeholder="Rua Exemplo, 123, Bairro, São Paulo - SP")
            
            if st.button("Simular Alerta", use_container_width=True):
                if email_usuario and endereco_usuario:
                    with col_email2:
                        st.markdown("**📧 Preview do Email de Alerta**")
                        
                        # Geocodificar o endereço do usuário
                        from geopy.geocoders import Nominatim
                        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
                        
                        try:
                            geolocator = Nominatim(user_agent="viasegura_energisa")
                            location = geolocator.geocode(endereco_usuario + ", São Paulo, Brazil", timeout=10)
                            
                            if location:
                                lat_usuario = location.latitude
                                lon_usuario = location.longitude
                                
                                # Buscar eventos próximos ao endereço do usuário
                                alertas_personalizados = []
                                
                                # 1. Buscar alagamentos próximos
                                alag_proximos = gdf_alagamento[
                                    (abs(gdf_alagamento.geometry.y - lat_usuario) < 0.01) & 
                                    (abs(gdf_alagamento.geometry.x - lon_usuario) < 0.01)
                                ]
                                
                                if len(alag_proximos) > 0:
                                    # Pegar um ponto específico de alagamento
                                    ponto_alag = alag_proximos.iloc[0]
                                    lat_alag = ponto_alag.geometry.y
                                    lon_alag = ponto_alag.geometry.x
                                    
                                    # Contar quantos alagamentos aconteceram nesse local específico
                                    alag_mesmo_local = gdf_alagamento[
                                        (abs(gdf_alagamento.geometry.y - lat_alag) < 0.002) & 
                                        (abs(gdf_alagamento.geometry.x - lon_alag) < 0.002)
                                    ]
                                    n_alag = len(alag_mesmo_local)
                                    nivel_alag = 'alto' if n_alag > 10 else ('medio' if n_alag > 5 else 'baixo')
                                    
                                    # Geocodificação reversa para pegar o endereço real
                                    endereco_alag = obter_endereco(lat_alag, lon_alag)
                                    
                                    alertas_personalizados.append({
                                        'tipo': 'Alagamento',
                                        'nivel': nivel_alag,
                                        'data': '01/02/2025',
                                        'hora': '14:30',
                                        'localizacao': endereco_alag,
                                        'historico': n_alag,
                                        'motivo': f'Área com histórico de {n_alag} ocorrências de alagamento'
                                    })
                                
                                # 2. Buscar acidentes próximos
                                acid_proximos = gdf_acidentes[
                                    (abs(gdf_acidentes.geometry.y - lat_usuario) < 0.01) & 
                                    (abs(gdf_acidentes.geometry.x - lon_usuario) < 0.01)
                                ]
                                
                                if len(acid_proximos) > 0:
                                    # Pegar um ponto específico de acidente diferente do alagamento
                                    ponto_acid = acid_proximos.iloc[min(5, len(acid_proximos)-1)]
                                    lat_acid = ponto_acid.geometry.y
                                    lon_acid = ponto_acid.geometry.x
                                    
                                    # Contar quantos acidentes aconteceram nesse local específico
                                    acid_mesmo_local = gdf_acidentes[
                                        (abs(gdf_acidentes.geometry.y - lat_acid) < 0.002) & 
                                        (abs(gdf_acidentes.geometry.x - lon_acid) < 0.002)
                                    ]
                                    n_acid = len(acid_mesmo_local)
                                    nivel_acid = 'alto' if n_acid > 50 else ('medio' if n_acid > 20 else 'baixo')
                                    
                                    # Geocodificação reversa para pegar o endereço real
                                    endereco_acid = obter_endereco(lat_acid, lon_acid)
                                    
                                    alertas_personalizados.append({
                                        'tipo': 'Acidente',
                                        'nivel': nivel_acid,
                                        'data': '01/02/2025',
                                        'hora': '18:45',
                                        'localizacao': endereco_acid,
                                        'historico': n_acid,
                                        'motivo': f'Área com histórico de {n_acid} acidentes envolvendo postes'
                                    })
                                
                                # Se não encontrou eventos próximos, criar alertas exemplo
                                if len(alertas_personalizados) == 0:
                                    alertas_personalizados = [
                                        {
                                            'tipo': 'Alagamento',
                                            'nivel': 'medio',
                                            'data': '01/02/2025',
                                            'hora': '14:30',
                                            'localizacao': 'Rua da Consolação, 1234 - Consolação',
                                            'historico': 8,
                                            'motivo': 'Área com histórico de 8 ocorrências de alagamento'
                                        },
                                        {
                                            'tipo': 'Acidente',
                                            'nivel': 'alto',
                                            'data': '01/02/2025',
                                            'hora': '18:45',
                                            'localizacao': 'Av. Paulista, 1578 - Bela Vista',
                                            'historico': 15,
                                            'motivo': 'Área com histórico de 15 acidentes envolvendo postes'
                                        }
                                    ]
                                
                                # Determinar nível máximo
                                nivel_max = 'baixo'
                                if any(a['nivel'] == 'alto' for a in alertas_personalizados):
                                    nivel_max = 'alto'
                                elif any(a['nivel'] == 'medio' for a in alertas_personalizados):
                                    nivel_max = 'medio'
                                
                                cor_alerta = {'alto': '#dc3545', 'medio': '#c3cc25', 'baixo': '#25aae2'}[nivel_max]
                                
                                st.markdown(f"""
                                <div style="border: 2px solid {cor_alerta}; padding: 20px; border-radius: 10px; background-color: #f8f9fa;">
                                    <h3 style="color: {cor_alerta};">⚠️ Alerta de Risco {nivel_max.upper()} - Energisa ViaSegura</h3>
                                    <p><strong>Para:</strong> {email_usuario}</p>
                                    <p><strong>Endereço monitorado:</strong> {endereco_usuario}</p>
                                    <hr>
                                    <p>Identificamos <strong>{len(alertas_personalizados)} evento(s) de risco</strong> próximo(s) à sua região em <strong>01/02/2025</strong>:</p>
                                """, unsafe_allow_html=True)
                                
                                for i, alerta in enumerate(alertas_personalizados, 1):
                                    cor_item = {'alto': '#dc3545', 'medio': '#c3cc25', 'baixo': '#25aae2'}[alerta['nivel']]
                                    st.markdown(f"""
                                    <div style="margin: 10px 0; padding: 10px; border-left: 4px solid {cor_item}; background: white;">
                                        <strong>{i}. {alerta['tipo']} - Risco {alerta['nivel'].upper()}</strong><br>
                                        📅 {alerta['data']} às {alerta['hora']}<br>
                                        📍 {alerta['localizacao']}<br>
                                        <em>{alerta['motivo']}</em>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                st.markdown("""
                                    <hr>
                                    <p><strong>Recomendações:</strong></p>
                                    <ul>
                                        <li>Evite circular próximo a postes em áreas de alto risco</li>
                                        <li>Em caso de chuva intensa, redobre a atenção com fiação elétrica</li>
                                        <li>Reporte qualquer anomalia: 0800-XXX-XXXX</li>
                                    </ul>
                                    <p style="color: #666; font-size: 0.9em;">Energisa ViaSegura © 2025</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("⚠️ Não foi possível geocodificar o endereço. Tente um endereço mais completo (com rua, número e bairro).")
                        
                        except (GeocoderTimedOut, GeocoderServiceError):
                            st.error("⚠️ Erro ao buscar localização. Tente novamente em alguns segundos.")
                        except Exception as e:
                            st.error(f"⚠️ Erro: {str(e)}")
                else:
                    st.warning("Preencha email e endereço para simular o alerta")
        
        # Insights principais
        st.markdown("---")
        st.subheader("Principais Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### Pontos Positivos
            - {}% das áreas apresentam **baixo risco**
            - Sistema de monitoramento cobrindo toda cidade
            - Dados históricos de 12+ anos para análise preditiva
            """.format(f"{perc_baixo:.1f}"))
        
        with col2:
            st.markdown("""
            ### Pontos de Atenção
            - {} áreas críticas **requerem ação imediata**
            - {} áreas em atenção precisam **monitoramento reforçado**
            - Sazonalidade: verão concentra mais riscos
            """.format(n_alto, n_medio))
    
    # ========== TAB 2: MAPA DE RISCOS ==========
    with tab2:
        st.header("Mapa Interativo de Riscos")
        
        # Filtrar por níveis selecionados
        grid_filtrado = grid_classificado[
            grid_classificado['categoria_risco'].isin(mostrar_niveis)
        ]
        
        st.info(f"Mostrando {len(grid_filtrado)} de {total_areas} áreas (filtro: {', '.join(mostrar_niveis)})")
        
        # Mapa
        if len(grid_filtrado) > 0:
            # Criar mapa com Plotly para ter controle de cores
            import plotly.express as px
            
            mapa_df = grid_filtrado[['latitude', 'longitude', 'indice_risco', 'categoria_risco']].copy()
            
            # Mapear cores
            color_map = {
                'baixo': '#25aae2',   # Azul
                'medio': '#c3cc25',   # Amarelo-verde
                'alto': '#dc3545'     # Vermelho
            }
            
            fig_mapa = px.scatter_mapbox(
                mapa_df,
                lat='latitude',
                lon='longitude',
                color='categoria_risco',
                color_discrete_map=color_map,
                category_orders={'categoria_risco': ['baixo', 'medio', 'alto']},
                hover_data={'indice_risco': ':.3f'},
                zoom=10,
                height=600,
                size_max=10
            )
            
            fig_mapa.update_layout(
                mapbox_style='open-street-map',
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=True,
                legend=dict(
                    title="Nível de Risco",
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01,
                    bgcolor="rgba(255, 255, 255, 0.8)"
                )
            )
            
            # Garantir que todas as categorias apareçam na legenda
            fig_mapa.update_traces(marker=dict(size=8))
            
            st.plotly_chart(fig_mapa, use_container_width=True)
            
            # Legenda
            col_leg1, col_leg2, col_leg3 = st.columns(3)
            with col_leg1:
                st.markdown("**Baixo**: Monitoramento regular")
            with col_leg2:
                st.markdown("**Médio**: Atenção reforçada")
            with col_leg3:
                st.markdown("**Alto**: Intervenção urgente")
        else:
            st.warning("Nenhuma área corresponde aos filtros selecionados.")
    
    # ========== TAB 3: ANÁLISE POR NÍVEIS ==========
    with tab3:
        st.header("Análise Detalhada por Nível de Risco")
        
        # Seletor de nível
        nivel_analise = st.selectbox(
            "Selecione o nível para análise detalhada:",
            options=['alto', 'medio', 'baixo'],
            format_func=lambda x: {'alto': 'ALTO RISCO', 'medio': 'MÉDIO RISCO', 'baixo': 'BAIXO RISCO'}[x]
        )
        
        areas_nivel = grid_classificado[grid_classificado['categoria_risco'] == nivel_analise]
        
        if len(areas_nivel) > 0:
            st.subheader(f"Encontradas {len(areas_nivel)} áreas com risco {nivel_analise.upper()}")
            
            # Estatísticas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Índice Médio",
                    f"{areas_nivel['indice_risco'].mean():.3f}"
                )
            
            with col2:
                st.metric(
                    "Índice Máximo",
                    f"{areas_nivel['indice_risco'].max():.3f}"
                )
            
            with col3:
                st.metric(
                    "Área Total",
                    f"{len(areas_nivel) * (grid_size * 111)**2:.1f} km²"
                )
            
            # Localização das áreas
            st.subheader("Onde estão essas áreas?")
            
            # Top 10 áreas
            top_areas = areas_nivel.nlargest(min(10, len(areas_nivel)), 'indice_risco')
            
            st.dataframe(
                top_areas[['latitude', 'longitude', 'indice_risco', 'categoria_risco']].style.format({
                    'latitude': '{:.4f}',
                    'longitude': '{:.4f}',
                    'indice_risco': '{:.3f}'
                }),
                use_container_width=True
            )
            
            # Mapa específico
            if st.checkbox(f"Ver mapa das áreas de risco {nivel_analise}"):
                st.map(top_areas[['latitude', 'longitude']])
            
            # Recomendações
            st.markdown("---")
            recomend = gerar_recomendacoes(nivel_analise, areas_nivel['indice_risco'].mean())
            
            cor_box = {'baixo': 'risk-baixo', 'medio': 'risk-medio', 'alto': 'risk-alto'}[nivel_analise]
            
            st.markdown(f"""
            <div class="risk-box {cor_box}">
                <h3>Recomendações para áreas de risco {nivel_analise.upper()}</h3>
                <p><strong>Prioridade:</strong> {recomend['prioridade']}</p>
                <p><strong>Frequência de Inspeção:</strong> {recomend['frequencia_inspecao']}</p>
                <p><strong>Investimento Sugerido:</strong> {recomend['investimento']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Ações recomendadas:**")
            for i, acao in enumerate(recomend['acoes'], 1):
                st.markdown(f"{i}. {acao}")
        else:
            st.success(f"Nenhuma área identificada com risco {nivel_analise}!")
    
    # ========== TAB 4: TENDÊNCIAS TEMPORAIS ==========
    with tab4:
        st.header("Análise de Tendências e Previsões")
        
        st.info("Esta seção mostra padrões históricos e projeções futuras baseadas em tendências.")
        
        # Análise de sazonalidade de acidentes
        st.subheader("Sazonalidade de Acidentes")
        
        if 'data' in gdf_acidentes.columns:
            sazon = analisar_sazonalidade(gdf_acidentes, 'data')
            
            meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            
            fig_sazon = go.Figure()
            fig_sazon.add_trace(go.Bar(
                x=[meses_nomes[int(m)-1] for m in sazon['mes']],
                y=sazon['frequencia'],
                marker=dict(
                    color=['#dc3545' if c else '#25aae2' for c in sazon['critico']],
                    line=dict(width=1, color='white')
                ),
                text=sazon['percentual'].apply(lambda x: f'{x:.1f}%'),
                textposition='outside'
            ))
            
            fig_sazon.update_layout(
                title="Distribuição Mensal de Acidentes (2013-2025)",
                xaxis_title="Mês",
                yaxis_title="Número de Acidentes",
                height=400
            )
            st.plotly_chart(fig_sazon, use_container_width=True)
            
            meses_criticos = sazon[sazon['critico']]['mes'].tolist()
            if meses_criticos:
                nomes_criticos = [meses_nomes[int(m)-1] for m in meses_criticos]
                st.warning(f"**Meses críticos:** {', '.join(nomes_criticos)} - Intensificar monitoramento!")
        
        st.markdown("---")
        
        # Projeção de risco
        st.subheader("Projeção de Cenários Futuros")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### Cenário OTIMISTA
            *Com intervenções nas áreas críticas*
            
            - Redução de **30-40%** nos riscos altos
            - Investimento em infraestrutura preventiva
            - Monitoramento contínuo efetivo
            
            **Resultado esperado (2026):**
            - Áreas críticas: -35%
            - Áreas seguras: +20%
            """)
        
        with col2:
            st.markdown("""
            ### Cenário CONSERVADOR
            *Mantendo condições atuais*
            
            - Manutenção dos níveis atuais
            - Possível aumento em 10-15% devido a urbanização
            - Riscos climáticos crescentes
            
            **Projeção (2026):**
            - Áreas críticas: +10%
            - Necessidade de ação urgente
            """)
    
    # ========== TAB 5: MODELO PREDITIVO ==========
    with tab5:
        st.header("Modelo Preditivo de Risco")
        
        st.markdown("""
        Este modelo utiliza dados históricos para projetar o nível de risco futuro.
        As previsões consideram tendências históricas, sazonalidade e padrões de crescimento urbano.
        """)
        
        # Controles de previsão
        col_control1, col_control2 = st.columns([2, 1])
        
        with col_control1:
            meses_previsao = st.slider(
                "Horizonte de previsão (meses)",
                min_value=1,
                max_value=24,
                value=12,
                help="Selecione quantos meses à frente deseja prever"
            )
        
        with col_control2:
            cenario = st.selectbox(
                "Cenário",
                options=['conservador', 'moderado', 'otimista'],
                format_func=lambda x: {
                    'conservador': 'Conservador (sem intervenções)',
                    'moderado': 'Moderado (intervenções parciais)',
                    'otimista': 'Otimista (intervenções completas)'
                }[x]
            )
        
        # Fatores de ajuste por cenário
        fatores = {
            'conservador': 1.15,  # Aumento de 15%
            'moderado': 1.0,      # Manutenção
            'otimista': 0.85      # Redução de 15%
        }
        
        fator_cenario = fatores[cenario]
        
        st.markdown("---")
        
        # Calcular projeções
        col_prev1, col_prev2 = st.columns([2, 1])
        
        with col_prev1:
            st.subheader("Projeção de Áreas por Nível de Risco")
            
            # Valores atuais
            n_alto_atual = distribuicao.get('alto', 0)
            n_medio_atual = distribuicao.get('medio', 0)
            n_baixo_atual = distribuicao.get('baixo', 0)
            
            # Criar dados de previsão mês a mês
            meses = list(range(0, meses_previsao + 1))
            
            # Tendências (simplificadas)
            # Alto risco: varia com o cenário
            alto_projecao = [n_alto_atual * (1 + (fator_cenario - 1) * (m / 12)) for m in meses]
            
            # Médio risco: redistribuição baseada no cenário
            medio_projecao = [n_medio_atual * (1 - (fator_cenario - 1) * 0.5 * (m / 12)) for m in meses]
            
            # Baixo risco: inversamente proporcional
            baixo_projecao = [total_areas - alto_projecao[i] - medio_projecao[i] for i in range(len(meses))]
            
            # Criar gráfico
            fig_pred = go.Figure()
            
            fig_pred.add_trace(go.Scatter(
                x=meses,
                y=alto_projecao,
                name='Alto Risco',
                mode='lines+markers',
                line=dict(color='#dc3545', width=3),
                fill='tonexty'
            ))
            
            fig_pred.add_trace(go.Scatter(
                x=meses,
                y=medio_projecao,
                name='Médio Risco',
                mode='lines+markers',
                line=dict(color='#c3cc25', width=3),
                fill='tonexty'
            ))
            
            fig_pred.add_trace(go.Scatter(
                x=meses,
                y=baixo_projecao,
                name='Baixo Risco',
                mode='lines+markers',
                line=dict(color='#25aae2', width=3),
                fill='tozeroy'
            ))
            
            fig_pred.update_layout(
                xaxis_title="Meses à frente",
                yaxis_title="Número de Áreas",
                hovermode='x unified',
                height=400,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_pred, use_container_width=True)
        
        with col_prev2:
            st.subheader("Métricas Previstas")
            
            # Valores finais (último mês)
            alto_final = int(alto_projecao[-1])
            medio_final = int(medio_projecao[-1])
            baixo_final = int(baixo_projecao[-1])
            
            # Variações
            var_alto = ((alto_final - n_alto_atual) / n_alto_atual * 100) if n_alto_atual > 0 else 0
            var_medio = ((medio_final - n_medio_atual) / n_medio_atual * 100) if n_medio_atual > 0 else 0
            var_baixo = ((baixo_final - n_baixo_atual) / n_baixo_atual * 100) if n_baixo_atual > 0 else 0
            
            st.metric(
                f"Áreas Críticas (+{meses_previsao}m)",
                alto_final,
                delta=f"{var_alto:+.1f}%",
                delta_color="inverse"
            )
            
            st.metric(
                f"Áreas Médias (+{meses_previsao}m)",
                medio_final,
                delta=f"{var_medio:+.1f}%"
            )
            
            st.metric(
                f"Áreas Seguras (+{meses_previsao}m)",
                baixo_final,
                delta=f"{var_baixo:+.1f}%"
            )
        
        st.markdown("---")
        
        # Premissas do Modelo
        st.subheader("Premissas do Modelo Preditivo")
        
        st.info(f"""
        **Cenário Selecionado:** {cenario.upper()}
        
        **Parâmetros:**
        - Fator de ajuste: {fator_cenario:.2f}x (variação mensal do risco)
        - Horizonte: {meses_previsao} meses à frente
        - Base histórica: Dados de 2013-2025 (13 anos)
        - Método: Projeção linear com ajuste por cenário
        
        **Interpretação dos cenários:**
        - **Conservador (1.15x):** Sem intervenções, risco aumenta 15% ao ano
        - **Moderado (1.0x):** Manutenção dos níveis atuais
        - **Otimista (0.85x):** Com intervenções, risco reduz 15% ao ano
        """)
        
        st.markdown("---")
        
        # Recomendações baseadas na previsão
        st.subheader("Recomendações Baseadas na Previsão")
        
        if var_alto > 5:
            st.error(f"""
            **ALERTA: Aumento significativo previsto (+{var_alto:.1f}%)**
            
            Ações recomendadas:
            - Acelerar programa de intervenções nas áreas críticas
            - Aumentar orçamento de manutenção preventiva
            - Implementar monitoramento 24/7 em áreas de alto risco
            - Revisar plano de contingência
            """)
        elif var_alto < -5:
            st.success(f"""
            **TENDÊNCIA POSITIVA: Redução prevista ({var_alto:.1f}%)**
            
            Manter estratégia atual:
            - Continuar programa de intervenções
            - Monitorar efetividade das ações
            - Documentar boas práticas
            - Expandir para novas áreas
            """)
        else:
            st.info(f"""
            **ESTABILIDADE: Manutenção dos níveis atuais**
            
            Recomendações:
            - Manter rotina de inspeções
            - Avaliar necessidade de intensificação
            - Preparar plano de contingência
            - Monitorar indicadores mensalmente
            """)
        
        # Disclaimer
        st.markdown("---")
        st.caption("""
        **Nota:** As projeções são baseadas em modelos simplificados e devem ser usadas como 
        orientação estratégica. Fatores externos (clima extremo, mudanças urbanas, eventos 
        inesperados) podem alterar significativamente os resultados.
        """)
    
    # ========== TAB 6: RECOMENDAÇÕES ESTRATÉGICAS ==========
    with tab6:
        st.header("Plano de Ação Estratégico")
        
        st.markdown("""
        ## Objetivo Principal
        **Reduzir riscos e garantir segurança da população próxima à rede elétrica**
        """)
        
        # Prioridades
        st.markdown("---")
        st.subheader("Prioridade 1: Áreas Críticas (Ação Imediata)")
        
        areas_criticas = grid_classificado[grid_classificado['categoria_risco'] == 'alto']
        
        if len(areas_criticas) > 0:
            st.error(f"**{len(areas_criticas)} áreas** requerem intervenção urgente!")
            
            recomend_alto = gerar_recomendacoes('alto', 0.8)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Ações Imediatas")
                for i, acao in enumerate(recomend_alto['acoes'][:3], 1):
                    st.markdown(f"**{i}.** {acao}")
            
            with col2:
                st.markdown("### Recursos Necessários")
                st.markdown(f"""
                - **Inspeções:** {recomend_alto['frequencia_inspecao']}
                - **Investimento:** {recomend_alto['investimento']}
                - **Equipes:** Mobilização imediata
                - **Prazo:** 30-60 dias
                """)
        else:
            st.success("Nenhuma área crítica identificada!")
        
        st.markdown("---")
        st.subheader("Prioridade 2: Áreas de Atenção (Médio Prazo)")
        
        areas_media = grid_classificado[grid_classificado['categoria_risco'] == 'medio']
        
        if len(areas_media) > 0:
            st.warning(f"**{len(areas_media)} áreas** em monitoramento preventivo")
            
            recomend_medio = gerar_recomendacoes('medio', 0.5)
            
            st.markdown("### Plano de Ação (90-180 dias)")
            for i, acao in enumerate(recomend_medio['acoes'], 1):
                st.markdown(f"{i}. {acao}")
        
        st.markdown("---")
        st.subheader("Áreas Seguras: Manutenção Preventiva")
        
        areas_baixa = grid_classificado[grid_classificado['categoria_risco'] == 'baixo']
        
        st.info(f"**{len(areas_baixa)} áreas** em regime de monitoramento padrão")
        
        st.markdown("""
        ### Manutenção Contínua
        - Inspeções trimestrais programadas
        - Registro de pequenos incidentes
        - Análise preditiva contínua
        - Investimento em prevenção
        """)
        
        st.markdown("---")
        st.subheader("Métricas de Sucesso")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **Meta 2026**
            - Reduzir áreas críticas em 50%
            - Zero acidentes fatais
            - Tempo de resposta < 2h
            """)
        
        with col2:
            st.markdown("""
            **Meta 2027**
            - 80% das áreas em baixo risco
            - Sistema preditivo com 90% acurácia
            - Cobertura 24/7
            """)
        
        with col3:
            st.markdown("""
            **Meta 2028**
            - 95% das áreas seguras
            - Rede inteligente completa
            - Resposta automatizada
            """)

except Exception as e:
    st.error(f"Erro ao processar dados: {str(e)}")
    import traceback
    with st.expander("Detalhes do erro"):
        st.code(traceback.format_exc())

# Rodapé
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>⚠️ <strong>Aviso:</strong> Dados projetados de 2022 a 2025 para fins de demonstração.<br>
        Análises baseadas em dados históricos reais de 1937-2025 (chuva), 2013-2022 (acidentes) e 2013-2025 (alagamento).</p>
        <p>Energisa ViaSegura © 2025 | Sistema Preditivo de Risco para Rede Elétrica</p>
    </div>
""", unsafe_allow_html=True)
