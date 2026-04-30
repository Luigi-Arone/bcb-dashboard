-- ====================================================
-- Schema: Dashboard Econômico Brasileiro
-- ====================================================

-- Tabela de metadados: descreve cada indicador monitorado
CREATE TABLE IF NOT EXISTS economic_series (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10)  NOT NULL UNIQUE, -- código da série no BCB
    name        VARCHAR(100) NOT NULL,        -- nome legível
    unit        VARCHAR(30)  NOT NULL,        -- ex: "% a.a.", "R$"
    frequency   VARCHAR(10)  NOT NULL,        -- "monthly" ou "daily"
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Tabela principal: valores históricos de cada indicador
CREATE TABLE IF NOT EXISTS economic_data (
    id          SERIAL PRIMARY KEY,
    series_code VARCHAR(10)  NOT NULL REFERENCES economic_series(code),
    date        DATE         NOT NULL,
    value       NUMERIC(12, 4) NOT NULL,
    collected_at TIMESTAMP DEFAULT NOW(),
 
    -- garante que não inserimos duplicatas
    UNIQUE (series_code, date)
);
 
-- Índices para acelerar queries analíticas
CREATE INDEX IF NOT EXISTS idx_econ_data_series_date
    ON economic_data (series_code, date DESC);
 
CREATE INDEX IF NOT EXISTS idx_econ_data_date
    ON economic_data (date DESC);
 
-- =============================================================
-- Seed: metadados das séries que vamos coletar
-- =============================================================

INSERT INTO economic_series (code, name, unit, frequency) VALUES
    ('433',   'IPCA',           '% ao mês',  'monthly'),
    ('432',   'Selic',          '% ao ano',  'daily'),
    ('1',     'Câmbio USD/BRL', 'R$',        'daily'),
    ('24369', 'Desemprego',     '% da PEA',  'monthly'),
    ('12', 'CDI', '% ao ano', 'daily')
ON CONFLICT (code) DO NOTHING;
