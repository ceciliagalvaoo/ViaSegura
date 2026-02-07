"""
Energisa ViaSegura - Sistema de Mapa Preditivo de Risco
"""

__version__ = "1.0.0"
__author__ = "Equipe Energisa"
__description__ = "Sistema preditivo de risco para acidentes com a rede elétrica"

# Importações principais para facilitar o uso
from .etl_chuva import processar_dados_chuva_completo
from .etl_acidentes import processar_dados_acidentes_completo
from .etl_alagamento import processar_dados_alagamento_completo
from .modelo_risco import ModeloRiscoViaSegura
from .cadastros_alertas import GerenciadorCadastros

__all__ = [
    'processar_dados_chuva_completo',
    'processar_dados_acidentes_completo',
    'processar_dados_alagamento_completo',
    'ModeloRiscoViaSegura',
    'GerenciadorCadastros',
]
