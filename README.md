# Energisa ViaSegura ⚡

> Sistema preditivo de risco para acidentes com a rede elétrica

## Sobre o Projeto

Este projeto foi desenvolvido para o **IDEATHON ENERGISA ONLINE**, um concurso cultural promovido pela Energisa S.A. com curadoria da Comunidade Hackathon Brasil.

### Desafio

O desafio busca **boas práticas e ideias inovadoras** que possam ser aplicadas na prática para **reduzir acidentes da população com a rede elétrica**, seja na cidade ou em zonas rurais. 

As propostas apresentadas devem priorizar a **Vida em primeiro lugar**, valor do Grupo Energisa.

### Nossa Solução

O **Energisa ViaSegura** é um sistema de mapeamento preditivo de risco que utiliza:

- 🤖 **Inteligência Artificial** para análise de dados históricos
- 📊 **Big Data** de acidentes, alagamentos e precipitação (1937-2025)
- 🗺️ **Geolocalização** para identificar áreas críticas
- 📧 **Sistema de alertas** para notificação preventiva
- 📈 **Modelos preditivos** para antecipar cenários de risco

## Funcionalidades

### Dashboard Interativo com 6 Módulos:

1. **Visão Executiva** - Panorama geral dos riscos, métricas e últimos alertas
2. **Mapa de Riscos** - Visualização geográfica com áreas classificadas por nível de perigo
3. **Análise por Níveis** - Detalhamento de áreas críticas, médias e seguras
4. **Tendências Temporais** - Sazonalidade e padrões históricos
5. **Modelo Preditivo** - Projeções futuras com cenários otimistas, moderados e conservadores
6. **Recomendações** - Plano de ação estratégico priorizado

### Diferenciais:

- ✅ Análise de **88 anos de dados** de precipitação (1937-2025)
- ✅ Mapeamento de **192.850 acidentes de trânsito** próximos a postes
- ✅ **66.367 pontos de alagamento** históricos (2013-2025)
- ✅ Sistema de **grid inteligente** para classificação espacial de risco
- ✅ **Geocodificação reversa** para endereços legíveis
- ✅ **Simulador de alertas por email** com previsão personalizada
- ✅ Interface responsiva com cores da marca Energisa

## Deploy

**Link da aplicação:** [[Deploy (Demo))]](https://viasegura.onrender.com/)


## Equipe

Desenvolvido por:

- **Cecília Galvão**
- **Pablo Azevedo**
- **Yuki Tanaka**

## Tecnologias Utilizadas

### Backend & Processamento:
- Python 3.13
- Pandas & GeoPandas (manipulação de dados geoespaciais)
- Shapely (geometrias)
- Geopy (geocodificação)

### Frontend & Visualização:
- Streamlit (dashboard interativo)
- Plotly (gráficos e mapas)
- HTML/CSS (customização visual)

### Dados:
- CSV (precipitação)
- KMZ (acidentes de trânsito)
- Shapefiles (áreas de alagamento)

## Estrutura do Projeto

```
energisa/
├── dashboard.py                    # Aplicação principal Streamlit
├── requirements.txt                # Dependências Python
├── data/                          # Dados brutos
│   ├── chuva_sp.csv              # Histórico de precipitação (1937-2025)
│   ├── acidente_transito.kmz     # Pontos de acidentes
│   └── alagamento/               # Shapefiles de alagamento (2013-2025)
├── src/                          # Módulos Python
│   ├── etl_chuva.py             # Processamento de dados de chuva
│   ├── etl_acidentes.py         # Processamento de acidentes
│   ├── etl_alagamento.py        # Processamento de alagamentos
│   ├── modelo_risco.py          # Cálculo de índice de risco
│   └── analise_temporal.py      # Classificação e recomendações
└── img/                          # Assets visuais
    └── Icone.svg                 # Logo Energisa
```

## Como Executar Localmente

### Pré-requisitos:
- Python 3.11+
- pip

### Passos:

1. Clone o repositório:
```bash
git clone [url-do-repositorio]
cd energisa
```

2. Crie e ative o ambiente virtual:
```bash
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Windows CMD:
.venv\Scripts\activate.bat

# Linux/Mac:
source .venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. **Obter os dados** (arquivo grande não incluído no repositório):

O arquivo `data/acidente_transito.kmz` (326 MB) não está no GitHub devido ao limite de tamanho, sendo a razão do deploy estar em uma versão demo inicial.

**Fontes oficiais dos dados:**
- **Chuva:** [DAEE SIBH](https://www.hidrologia.daee.sp.gov.br/) - Estação Mirante de Santana
- **Acidentes:** [GeoSampa](https://geosampa.prefeitura.sp.gov.br/) - Camada de acidentes de trânsito
- **Alagamento:** [GeoSampa](https://geosampa.prefeitura.sp.gov.br/) - Shapefiles de risco de ocorrência
- **Contato:** Entre em contato com a equipe para receber os arquivos já processados

Certifique-se de que os arquivos estejam em:
- `data/chuva_sp.csv`
- `data/acidente_transito.kmz`
- `data/alagamento/` (shapefiles 2013-2025)

5. Execute o dashboard:
```bash
streamlit run dashboard.py
```

6. Acesse no navegador:
```
http://localhost:8501
```

## Dados Utilizados

### Precipitação (1937-2025)
- **29.104 registros diários**
- Estação: Mirante de Santana - São Paulo
- Média: 3.9mm/dia, 116mm/mês
- **Fonte:** Centro de Gerenciamento de Emergências Climáticas (CGE) - Prefeitura de São Paulo

### Acidentes de Trânsito (2013-2022 + projeção até 2025)
- **192.850 eventos** próximos a postes
- Cobertura: Município de São Paulo
- Lat: -23.99 a -23.36, Lon: -46.82 a -46.37
- **Fonte:** Companhia de Engenharia de Tráfego (CET-SP) - Dados Abertos da Prefeitura de São Paulo

### Áreas de Alagamento (2013-2025)
- **66.367 pontos** de risco de alagamento
- 13 shapefiles anuais (SIRGAS)
- Variação: 2.614 a 8.788 pontos/ano
- **Fonte:** GeoSampa - Sistema de Informações Geográficas da Prefeitura de São Paulo

## Metodologia

### 1. Divisão Espacial - Grid Inteligente

A cidade é dividida em **736 células** usando um grid geoespacial de **0.02° (~2.2km por célula)**. Cada célula representa uma área específica onde calculamos o índice de risco agregado.

**Configuração:**
- Grid configurável: 0.01° a 0.05° (1.1km a 5.5km por célula)
- Cobertura total da área de São Paulo
- Sistema de coordenadas: SIRGAS/WGS84

### 2. Cálculo de Scores por Fator de Risco

#### Score de Acidentes de Trânsito

**Método:** Densidade espacial de eventos

```python
Para cada célula do grid:
  1. Contar acidentes dentro da célula (raio de busca)
  2. Aplicar kernel density estimation (KDE)
  3. Normalizar: Score = (densidade_célula - min) / (max - min)
  4. Resultado: valor entre 0.0 e 1.0
```

**Lógica:**
- Células com **muitos acidentes** próximos a postes → Score alto (0.7 - 1.0)
- Células com **poucos acidentes** → Score baixo (0.0 - 0.3)
- Considera concentração espacial, não apenas contagem

#### Score de Alagamento

**Método:** Proximidade e recorrência de pontos de alagamento

```python
Para cada célula do grid:
  1. Buscar pontos de alagamento dentro da célula
  2. Considerar histórico de 13 anos (2013-2025)
  3. Peso maior para anos recentes (decaimento temporal)
  4. Normalizar: Score = (pontos_célula - min) / (max - min)
  5. Resultado: valor entre 0.0 e 1.0
```

**Lógica:**
- Células com **histórico recorrente** de alagamento → Score alto
- Alagamentos **recentes** têm peso maior
- Áreas sem histórico → Score 0.0

#### Score de Chuva

**Método:** Intensidade de precipitação e sazonalidade

```python
Score baseado em precipitação média:
  - Chuva Leve (< 10mm/dia): Score = 0.2
  - Chuva Moderada (10-50mm/dia): Score = 0.5
  - Chuva Intensa (> 50mm/dia): Score = 0.8
  - Chuva Muito Intensa (> 100mm/dia): Score = 1.0
```

**Lógica:**
- Considera **padrões sazonais** (verão = maior risco)
- Dados de 88 anos (1937-2025) para identificar tendências
- Precipitações extremas aumentam risco de danos à rede

### 3. Índice de Risco Final

**Fórmula Ponderada:**

```
Índice de Risco = (W₁ × Score_Acidentes) + 
                  (W₂ × Score_Alagamento) + 
                  (W₃ × Score_Chuva)

Onde:
  W₁ = Peso Acidentes (padrão: 0.40 ou 40%)
  W₂ = Peso Alagamento (padrão: 0.30 ou 30%)
  W₃ = Peso Chuva (padrão: 0.30 ou 30%)
  
Restrição: W₁ + W₂ + W₃ = 1.0
```

**Exemplo de Cálculo:**

```
Célula X:
  - Score Acidentes = 0.85 (alta densidade de acidentes)
  - Score Alagamento = 0.60 (histórico moderado)
  - Score Chuva = 0.50 (precipitação média)

Índice de Risco = (0.40 × 0.85) + (0.30 × 0.60) + (0.30 × 0.50)
                = 0.34 + 0.18 + 0.15
                = 0.67
```

### 4. Classificação de Áreas

**Categorização por Threshold:**

| Índice de Risco | Categoria | Cor | Ação Recomendada |
|-----------------|-----------|-----|------------------|
| **0.00 - 0.33** | **Baixo** | 🔵 Azul (#25aae2) | Monitoramento regular trimestral |
| **0.33 - 0.66** | **Médio** | 🟡 Amarelo (#c3cc25) | Atenção reforçada, inspeções mensais |
| **0.66 - 1.00** | **Alto** | 🔴 Vermelho (#dc3545) | Intervenção urgente, inspeções semanais |

### 5. Modelo Preditivo

**Projeção de Cenários Futuros:**

```python
Projeção(meses) = Valor_Atual × (1 + Taxa_Crescimento × meses/12)

Taxas por Cenário:
  - Conservador: +15% ao ano (sem intervenções)
  - Moderado: 0% ao ano (manutenção do status quo)
  - Otimista: -15% ao ano (com intervenções eficazes)
```

**Validação:**
- Análise de sazonalidade (identificação de meses críticos)
- Tendências históricas de 13 anos
- Correlação entre fatores de risco

### 6. Validação e Precisão

**Métricas de Qualidade:**
- ✅ Cobertura espacial: 100% da área urbana de São Paulo
- ✅ Resolução temporal: Dados diários (chuva), eventos pontuais (acidentes/alagamento)
- ✅ Histórico: 13 anos completos (2013-2025) + 88 anos de precipitação
- ✅ Atualização: Sistema preparado para ingestão contínua de novos dados

## Impacto Esperado

- ⚡ **Redução de acidentes** com rede elétrica através de prevenção
- 🎯 **Priorização de investimentos** em áreas críticas
- 📍 **Monitoramento inteligente** com alertas georreferenciados
- 📊 **Tomada de decisão baseada em dados** para equipes de campo
- 🔮 **Antecipação de riscos** com modelos preditivos

## 📄 Licença

Este projeto foi desenvolvido para o Ideathon Energisa 2026.

---

**Energisa ViaSegura** - Soluções para minimizar riscos e garantir maior segurança da população próxima à rede elétrica. ⚡🛡️
