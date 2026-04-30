#!/bin/bash

echo "🚀 Iniciando bcb-dashboard..."

# Ativa o ambiente virtual
source venv/bin/activate

# Sobe o banco
echo "📦 Subindo PostgreSQL..."
docker-compose up -d

# Aguarda o banco estar pronto
echo "⏳ Aguardando o banco iniciar..."
sleep 5

# Aplica o schema
echo "🗄️ Aplicando schema..."
PGPASSWORD=postgres psql -h localhost -U postgres -d bcb_dashboard -f sql/schema.sql

# Coleta os dados
echo "📡 Coletando dados do Banco Central..."
python -m src.collectors.bcb

# Sobe o dashboard
echo "📊 Iniciando dashboard..."
streamlit run dashboard/app.py
