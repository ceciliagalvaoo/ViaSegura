"""
Módulo de Análise Temporal de Risco
Calcula tendências históricas e projeções futuras
"""
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats


def calcular_tendencia_temporal(df_risco, anos=[2020, 2021, 2022, 2023, 2024]):
    """
    Calcula tendência de risco ao longo dos anos
    
    Args:
        df_risco: DataFrame com colunas [ano, indice_risco]
        anos: Lista de anos para análise
    
    Returns:
        dict com estatísticas de tendência
    """
    # Filtrar dados disponíveis
    df_filtrado = df_risco[df_risco['ano'].isin(anos)].copy()
    
    # Calcular média e desvio padrão por ano
    stats_anuais = df_filtrado.groupby('ano')['indice_risco'].agg([
        ('media', 'mean'),
        ('std', 'std'),
        ('max', 'max'),
        ('p95', lambda x: np.percentile(x, 95))
    ]).reset_index()
    
    # Calcular regressão linear
    if len(stats_anuais) >= 2:
        x = stats_anuais['ano'].values
        y = stats_anuais['media'].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            'stats_anuais': stats_anuais,
            'tendencia': {
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'direcao': 'crescente' if slope > 0 else 'decrescente',
                'significativo': p_value < 0.05
            }
        }
    
    return {
        'stats_anuais': stats_anuais,
        'tendencia': None
    }


def projetar_risco_futuro(tendencia, anos_futuros=[2026, 2027, 2028]):
    """
    Projeta risco para anos futuros com base na tendência
    
    Args:
        tendencia: dict retornado por calcular_tendencia_temporal
        anos_futuros: Lista de anos para projetar
    
    Returns:
        DataFrame com projeções
    """
    if tendencia['tendencia'] is None:
        return pd.DataFrame()
    
    slope = tendencia['tendencia']['slope']
    intercept = tendencia['tendencia']['intercept']
    
    projecoes = []
    for ano in anos_futuros:
        risco_proj = slope * ano + intercept
        
        # Limitar projeção entre valores realistas
        risco_proj = max(0, min(1, risco_proj))
        
        projecoes.append({
            'ano': ano,
            'risco_projetado': risco_proj,
            'confianca': 'baixa' if ano > 2027 else 'media'
        })
    
    return pd.DataFrame(projecoes)


def analisar_sazonalidade(df_eventos, coluna_data='data'):
    """
    Analisa padrões sazonais de eventos (chuva, acidentes, alagamentos)
    
    Args:
        df_eventos: DataFrame com coluna de data
        coluna_data: Nome da coluna com datas
    
    Returns:
        DataFrame com estatísticas por mês
    """
    df = df_eventos.copy()
    df['mes'] = pd.to_datetime(df[coluna_data]).dt.month
    df['ano'] = pd.to_datetime(df[coluna_data]).dt.year
    
    # Agrupar por mês
    sazonalidade = df.groupby('mes').size().reset_index(name='frequencia')
    sazonalidade['percentual'] = (sazonalidade['frequencia'] / sazonalidade['frequencia'].sum()) * 100
    
    # Identificar meses críticos (acima da média + 1 std)
    media = sazonalidade['frequencia'].mean()
    std = sazonalidade['frequencia'].std()
    sazonalidade['critico'] = sazonalidade['frequencia'] > (media + std)
    
    return sazonalidade


def classificar_areas_por_risco(grid_risco, thresholds={'baixo': 0.3, 'medio': 0.6}):
    """
    Classifica áreas do grid em categorias de risco
    
    Args:
        grid_risco: DataFrame com coluna 'indice_risco'
        thresholds: Limites para classificação
    
    Returns:
        DataFrame com categoria adicional
    """
    df = grid_risco.copy()
    
    def classificar(valor):
        if pd.isna(valor):
            return 'sem_dados'
        elif valor < thresholds['baixo']:
            return 'baixo'
        elif valor < thresholds['medio']:
            return 'medio'
        else:
            return 'alto'
    
    df['categoria_risco'] = df['indice_risco'].apply(classificar)
    
    return df


def gerar_recomendacoes(categoria_risco, intensidade):
    """
    Gera recomendações práticas baseadas no nível de risco
    
    Args:
        categoria_risco: 'baixo', 'medio' ou 'alto'
        intensidade: valor numérico do índice (0-1)
    
    Returns:
        dict com recomendações
    """
    recomendacoes = {
        'baixo': {
            'prioridade': 'Monitoramento',
            'acoes': [
                'Manter inspeções regulares da rede',
                'Monitorar padrões climáticos',
                'Registrar pequenos incidentes para análise'
            ],
            'frequencia_inspecao': 'Trimestral',
            'investimento': 'Manutenção preventiva básica'
        },
        'medio': {
            'prioridade': 'Atenção',
            'acoes': [
                'Aumentar frequência de inspeções',
                'Avaliar necessidade de reforço estrutural',
                'Implementar sensores de monitoramento',
                'Treinar equipes para resposta rápida'
            ],
            'frequencia_inspecao': 'Mensal',
            'investimento': 'Reforço seletivo + monitoramento'
        },
        'alto': {
            'prioridade': 'CRÍTICO',
            'acoes': [
                '⚠️ INSPEÇÃO IMEDIATA NECESSÁRIA',
                'Avaliar realocação de cabos subterrâneos',
                'Instalar sistema de proteção adicional',
                'Implementar monitoramento 24/7',
                'Plano de contingência e evacuação',
                'Sinalização de segurança reforçada'
            ],
            'frequencia_inspecao': 'Semanal ou contínua',
            'investimento': 'Intervenção estrutural urgente'
        }
    }
    
    return recomendacoes.get(categoria_risco, recomendacoes['medio'])
