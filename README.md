# 📊 Dashboard Econômico Brasileiro

Pipeline de dados que coleta indicadores econômicos do Banco Central do Brasil, armazena em PostgreSQL e exibe em um dashboard interativo com Streamlit.

## 🗂️ Indicadores monitorados

| Indicador | Série BCB | Descrição |
|-----------|-----------|-----------|
| IPCA | 433 | Inflação mensal (%) |
| Selic | 432 | Taxa básica de juros (% a.a.) |
| Câmbio USD | 1 | Dólar comercial (R$) |
| Desemprego | 24369 | Taxa de desocupação IBGE (%) |

## 🏗️ Arquitetura

```
API Banco Central
      │
      ▼
src/collectors/bcb.py     ← Coleta os dados via requests
      │
      ▼
src/db/loader.py          ← Carrega no PostgreSQL com psycopg2
      │
      ▼
PostgreSQL                ← Armazena séries temporais
  ├── economic_series     (metadados de cada indicador)
  └── economic_data       (valores históricos)
      │
      ▼
src/analysis/queries.py   ← Queries analíticas (CTEs, window functions)
      │
      ▼
dashboard/app.py          ← Streamlit: visualização interativa
```

## 🚀 Como rodar

### Pré-requisitos
- Python 3.11
- Docker e Docker Compose

### Inicialização rápida
```bash
./setup.sh
```

### Inicialização manual

### 1. Suba o banco
```bash
docker-compose up -d
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Crie as tabelas
```bash
psql -h localhost -U postgres -d bcb_dashboard -f sql/schema.sql
```

### 4. Colete os dados
```bash
python -m src.collectors.bcb
```

### 5. Rode o dashboard
```bash
streamlit run dashboard/app.py
```

## 📁 Estrutura de pastas

```
bcb-dashboard/
├── README.md
├── docker-compose.yml
├── requirements.txt
├── sql/
│   ├── schema.sql          # Criação das tabelas
│   └── queries.sql         # Queries analíticas documentadas
├── src/
│   ├── collectors/
│   │   └── bcb.py          # Coleta da API do BCB
│   ├── db/
│   │   ├── connection.py   # Gerenciamento de conexão
│   │   └── loader.py       # Inserção dos dados
│   └── analysis/
│       └── queries.py      # Queries para o dashboard
└── dashboard/
    └── app.py              # Interface Streamlit
```
