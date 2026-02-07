"""
Módulo para cálculo do Índice de Risco ViaSegura.
Combina dados de acidentes, chuva e alagamentos para calcular risco por área.
"""
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from scipy.spatial import cKDTree


class ModeloRiscoViaSegura:
    """
    Modelo de risco que combina múltiplas fontes de dados para calcular
    o índice de risco de acidentes com a rede elétrica.
    """
    
    def __init__(self, pesos=None):
        """
        Inicializa o modelo de risco.
        
        Args:
            pesos: Dicionário com pesos para cada fator
                  {'acidentes': 0.4, 'alagamento': 0.3, 'chuva': 0.3}
        """
        if pesos is None:
            self.pesos = {
                'acidentes': 0.40,      # Histórico de acidentes
                'alagamento': 0.30,     # Risco de alagamento
                'chuva': 0.30           # Intensidade de chuva
            }
        else:
            self.pesos = pesos
        
        # Normalizar pesos para somar 1
        total = sum(self.pesos.values())
        self.pesos = {k: v/total for k, v in self.pesos.items()}
    
    
    def criar_grid_cidade(self, bounds, grid_size=0.01):
        """
        Cria uma grade regular para a área de interesse.
        
        Args:
            bounds: Tupla (min_lon, min_lat, max_lon, max_lat)
            grid_size: Tamanho da célula em graus
            
        Returns:
            GeoDataFrame com grade
        """
        min_lon, min_lat, max_lon, max_lat = bounds
        
        # Criar pontos da grade
        lons = np.arange(min_lon, max_lon, grid_size)
        lats = np.arange(min_lat, max_lat, grid_size)
        
        grid_points = []
        for lon in lons:
            for lat in lats:
                grid_points.append({
                    'longitude': lon,
                    'latitude': lat,
                    'grid_x': lon,
                    'grid_y': lat
                })
        
        df_grid = pd.DataFrame(grid_points)
        geometry = [Point(xy) for xy in zip(df_grid['longitude'], df_grid['latitude'])]
        gdf_grid = gpd.GeoDataFrame(df_grid, geometry=geometry, crs='EPSG:4326')
        
        return gdf_grid
    
    
    def calcular_score_acidentes(self, gdf_grid, gdf_acidentes, raio_km=1.0):
        """
        Calcula score de risco baseado em histórico de acidentes.
        
        Args:
            gdf_grid: GeoDataFrame com grade
            gdf_acidentes: GeoDataFrame com acidentes
            raio_km: Raio de busca em km
            
        Returns:
            Series com scores normalizados (0-1)
        """
        if gdf_acidentes is None or gdf_acidentes.empty:
            return pd.Series(0, index=gdf_grid.index)
        
        # Converter raio de km para graus (aproximado)
        raio_graus = raio_km / 111.0
        
        # Usar KDTree para busca espacial eficiente
        tree = cKDTree(gdf_acidentes[['longitude', 'latitude']].values)
        
        scores = []
        for idx, row in gdf_grid.iterrows():
            # Buscar acidentes próximos
            indices = tree.query_ball_point([row['longitude'], row['latitude']], raio_graus)
            
            if indices:
                # Somar número de acidentes (com peso decrescente pela distância)
                acidentes_proximos = gdf_acidentes.iloc[indices]
                if 'num_acidentes' in acidentes_proximos.columns:
                    score = acidentes_proximos['num_acidentes'].sum()
                else:
                    score = len(indices)
            else:
                score = 0
            
            scores.append(score)
        
        # Normalizar para 0-1
        scores = pd.Series(scores)
        if scores.max() > 0:
            scores = scores / scores.max()
        
        return scores
    
    
    def calcular_score_alagamento(self, gdf_grid, gdf_alagamento, raio_km=1.0):
        """
        Calcula score de risco baseado em histórico de alagamentos.
        
        Args:
            gdf_grid: GeoDataFrame com grade
            gdf_alagamento: GeoDataFrame com alagamentos
            raio_km: Raio de busca em km
            
        Returns:
            Series com scores normalizados (0-1)
        """
        if gdf_alagamento is None or gdf_alagamento.empty:
            return pd.Series(0, index=gdf_grid.index)
        
        raio_graus = raio_km / 111.0
        tree = cKDTree(gdf_alagamento[['longitude', 'latitude']].values)
        
        scores = []
        for idx, row in gdf_grid.iterrows():
            indices = tree.query_ball_point([row['longitude'], row['latitude']], raio_graus)
            
            if indices:
                alagamentos_proximos = gdf_alagamento.iloc[indices]
                
                # Considerar nível de risco se disponível
                if 'risco_normalizado' in alagamentos_proximos.columns:
                    peso_risco = {'Alto': 3, 'Médio': 2, 'Baixo': 1, 'Não Classificado': 1}
                    score = sum([peso_risco.get(r, 1) for r in alagamentos_proximos['risco_normalizado']])
                elif 'total_ocorrencias' in alagamentos_proximos.columns:
                    score = alagamentos_proximos['total_ocorrencias'].sum()
                else:
                    score = len(indices)
            else:
                score = 0
            
            scores.append(score)
        
        scores = pd.Series(scores)
        if scores.max() > 0:
            scores = scores / scores.max()
        
        return scores
    
    
    def calcular_score_chuva(self, intensidade_chuva):
        """
        Calcula score de risco baseado na intensidade de chuva atual/prevista.
        
        Args:
            intensidade_chuva: String ('Seco', 'Fraca', 'Moderada', 'Forte', 'Muito Forte')
                              ou valor numérico em mm
            
        Returns:
            Score normalizado (0-1)
        """
        if isinstance(intensidade_chuva, str):
            mapa_intensidade = {
                'Seco': 0.0,
                'Fraca': 0.2,
                'Moderada': 0.5,
                'Forte': 0.8,
                'Muito Forte': 1.0
            }
            return mapa_intensidade.get(intensidade_chuva, 0.0)
        else:
            # Se for valor numérico, normalizar
            if intensidade_chuva <= 0:
                return 0.0
            elif intensidade_chuva < 5:
                return 0.2
            elif intensidade_chuva < 25:
                return 0.5
            elif intensidade_chuva < 50:
                return 0.8
            else:
                return 1.0
    
    
    def calcular_fator_temporal(self, hora=None, dia_semana=None):
        """
        Calcula fator multiplicador baseado em hora do dia e dia da semana.
        
        Args:
            hora: Hora do dia (0-23)
            dia_semana: Dia da semana (0=segunda, 6=domingo)
            
        Returns:
            Fator multiplicador (0.5 - 1.5)
        """
        fator = 1.0
        
        # Horários de pico (maior risco)
        if hora is not None:
            if 7 <= hora <= 9 or 17 <= hora <= 19:
                fator *= 1.3  # Horário de pico
            elif 22 <= hora or hora <= 5:
                fator *= 1.2  # Período noturno (visibilidade reduzida)
            else:
                fator *= 1.0
        
        # Fim de semana (padrão diferente)
        if dia_semana is not None:
            if dia_semana >= 5:  # Sábado ou domingo
                fator *= 0.9
        
        return fator
    
    
    def calcular_indice_risco(self, score_acidentes, score_alagamento, score_chuva=None,
                             gdf_grid=None, gdf_acidentes=None, gdf_alagamento=None, 
                             intensidade_chuva='Seco', hora=None, dia_semana=None):
        """
        Calcula o índice de risco composto para cada célula da grade.
        
        Args:
            score_acidentes: Series com scores já calculados OU GeoDataFrame com acidentes
            score_alagamento: Series com scores já calculados OU GeoDataFrame com alagamentos
            score_chuva: Series/float com scores já calculados OU None (calcular)
            gdf_grid: GeoDataFrame com grade (necessário se passar GeoDataFrames)
            gdf_acidentes: GeoDataFrame com acidentes (se score_acidentes for GDF)
            gdf_alagamento: GeoDataFrame com alagamentos (se score_alagamento for GDF)
            intensidade_chuva: Intensidade de chuva atual/prevista
            hora: Hora do dia (opcional)
            dia_semana: Dia da semana (opcional)
            
        Returns:
            Series com índice de risco calculado
        """
        # Se recebeu GeoDataFrames, calcular scores
        if isinstance(score_acidentes, gpd.GeoDataFrame):
            if gdf_grid is None:
                raise ValueError("gdf_grid necessário quando passar GeoDataFrame")
            score_acidentes = self.calcular_score_acidentes(gdf_grid, score_acidentes)
        
        if isinstance(score_alagamento, gpd.GeoDataFrame):
            if gdf_grid is None:
                raise ValueError("gdf_grid necessário quando passar GeoDataFrame")
            score_alagamento = self.calcular_score_alagamento(gdf_grid, score_alagamento)
        
        if score_chuva is None:
            score_chuva = self.calcular_score_chuva(intensidade_chuva)
        
        # Calcular índice composto
        indice_risco = (
            self.pesos['acidentes'] * score_acidentes +
            self.pesos['alagamento'] * score_alagamento +
            self.pesos['chuva'] * score_chuva
        )
        
        # Aplicar fator temporal
        fator_temporal = self.calcular_fator_temporal(hora, dia_semana)
        indice_risco = indice_risco * fator_temporal
        
        # Garantir que está entre 0 e 1
        indice_risco = indice_risco.clip(0, 1)
        
        # Se não tiver grid, retornar apenas o índice
        if gdf_grid is None:
            return indice_risco
        
        # Adicionar ao grid
        gdf_resultado = gdf_grid.copy()
        gdf_resultado['score_acidentes'] = score_acidentes
        gdf_resultado['score_alagamento'] = score_alagamento
        gdf_resultado['score_chuva'] = score_chuva
        gdf_resultado['indice_risco'] = indice_risco
        
        # Classificar risco
        gdf_resultado['classificacao_risco'] = pd.cut(
            indice_risco,
            bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
            labels=['Muito Baixo', 'Baixo', 'Médio', 'Alto', 'Muito Alto'],
            include_lowest=True
        )
        
        return gdf_resultado
    
    
    def identificar_trechos_criticos(self, gdf_risco, top_n=20):
        """
        Identifica os trechos mais críticos (maior risco).
        
        Args:
            gdf_risco: GeoDataFrame com índices de risco
            top_n: Número de trechos a retornar
            
        Returns:
            GeoDataFrame com os trechos mais críticos
        """
        gdf_sorted = gdf_risco.sort_values('indice_risco', ascending=False)
        return gdf_sorted.head(top_n)
    
    
    def gerar_recomendacoes(self, gdf_criticos):
        """
        Gera recomendações para os trechos críticos.
        
        Args:
            gdf_criticos: GeoDataFrame com trechos críticos
            
        Returns:
            DataFrame com recomendações
        """
        recomendacoes = []
        
        for idx, row in gdf_criticos.iterrows():
            risco = row['indice_risco']
            score_acidentes = row.get('score_acidentes', 0)
            score_alagamento = row.get('score_alagamento', 0)
            
            rec = {
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'indice_risco': risco,
                'recomendacoes': []
            }
            
            # Recomendações baseadas nos scores
            if score_acidentes > 0.6:
                rec['recomendacoes'].append('Instalar defensas ao redor de postes')
                rec['recomendacoes'].append('Reforçar sinalização de trânsito')
                rec['recomendacoes'].append('Campanha educativa sobre direção segura')
            
            if score_alagamento > 0.6:
                rec['recomendacoes'].append('Avaliar drenagem da via')
                rec['recomendacoes'].append('Instalar sistema de alerta de alagamento')
                rec['recomendacoes'].append('Elevar equipamentos elétricos')
            
            if risco > 0.8:
                rec['recomendacoes'].append('AÇÃO PRIORITÁRIA: Inspeção técnica urgente')
                rec['recomendacoes'].append('Posicionar equipe de resposta rápida')
            
            rec['recomendacoes_texto'] = '; '.join(rec['recomendacoes'])
            recomendacoes.append(rec)
        
        return pd.DataFrame(recomendacoes)


if __name__ == '__main__':
    # Teste do modelo
    modelo = ModeloRiscoViaSegura()
    print("Modelo ViaSegura inicializado")
    print(f"Pesos: {modelo.pesos}")
    
    # Teste de score de chuva
    print(f"\nScore chuva forte: {modelo.calcular_score_chuva('Forte')}")
    print(f"Score chuva 30mm: {modelo.calcular_score_chuva(30)}")
