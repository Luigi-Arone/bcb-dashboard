# 📊 Dashboard Econômico Brasileiro

Pipeline de dados que coleta indicadores econômicos do Banco Central do Brasil, armazena em PostgreSQL e exibe em um dashboard interativo com Streamlit — incluindo expectativa de mercado para Selic e CDI via API Focus (BCB).

## 🗂️ Indicadores monitorados

| Indicador | Série BCB | Descrição |
|-----------|-----------|-----------|
| IPCA | 433 | Inflação mensal (%) |
| Selic | 432 | Taxa básica de juros (% a.a.) |
| Câmbio USD | 1 | Dólar comercial (R$) |
| Desemprego | 24369 | Taxa de desocupação IBGE (%) |
| CDI | 12 | Certificado de Depósito Interbancário (% a.a.) |

## 🏗️ Arquitetura

```
API Banco Central (SGS)         API Focus (BCB)
        │                              │
        ▼                              ▼
src/collectors/bcb.py     ←→   src/analysis/queries.py
        │                              │
        ▼                              │
src/db/loader.py                       │
        │                              │
        ▼                              │
PostgreSQL                             │
  ├── economic_series                  │
  └── economic_data  ─────────────────┘
        │
        ▼
src/analysis/queries.py   ← Queries analíticas (CTEs, window functions)
        │
        ▼
dashboard/app.py          ← Streamlit: visualização interativa com dark mode
```

## 📊 Funcionalidades

- Histórico de todos os indicadores com slider de período ajustável
- IPCA acumulado nos últimos 12 meses
- Variação mensal do câmbio vs IPCA
- Juros reais (Selic − IPCA anualizado) com destaque para períodos negativos
- Selic e CDI históricos lado a lado
- **Expectativa de mercado para Selic e CDI** por reunião do Copom via API Focus (BCB)

## 🚀 Como rodar

### Pré-requisitos
- Python 3.11
- Docker e Docker Compose

### Inicialização rápida
```bash
./setup.sh
```

### Inicialização manual

**1. Suba o banco**
```bash
docker-compose up -d
```

**2. Crie o ambiente virtual e instale as dependências**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Crie as tabelas**
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d bcb_dashboard -f sql/schema.sql
```

**4. Colete os dados**
```bash
python -m src.collectors.bcb
```

**5. Rode o dashboard**
```bash
streamlit run dashboard/app.py
```

## 🔄 Atualização dos dados

A coleta é manual. Para atualizar os dados a qualquer momento:

```bash
python -m src.collectors.bcb
```

A API do Banco Central disponibiliza dados dos últimos 10 anos. O intervalo é calculado automaticamente a partir da data atual. Séries diárias (Selic, Câmbio, CDI) são coletadas ano a ano para evitar timeout.

## 📁 Estrutura de pastas

```
bcb-dashboard/
├── README.md
├── LICENSE                     # MIT License
├── setup.sh                    # Inicialização rápida
├── docker-compose.yml
├── requirements.txt
├── sql/
│   ├── schema.sql              # Criação das tabelas e seed de metadados
│   └── queries.sql             # Queries analíticas documentadas
├── src/
│   ├── collectors/
│   │   └── bcb.py              # Coleta da API do BCB com retry automático
│   ├── db/
│   │   ├── connection.py       # Gerenciamento de conexão
│   │   └── loader.py           # Inserção dos dados com upsert
│   └── analysis/
│       └── queries.py          # Queries analíticas + expectativa Focus
└── dashboard/
    └── app.py                  # Interface Streamlit com dark mode
```

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.11 | Linguagem principal |
| PostgreSQL 15 | Banco de dados |
| psycopg2 | Conexão Python → PostgreSQL |
| requests | Coleta das APIs do BCB e Focus |
| pandas | Manipulação dos dados |
| Streamlit | Dashboard interativo |
| Plotly | Visualizações |
| Docker | Ambiente do banco de dados |

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).