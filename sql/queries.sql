-- =============================================================
-- Queries Analíticas — bcb-dashboard
-- =============================================================


-- -------------------------------------------------------------
-- 1. Últimos 12 meses de cada indicador (última leitura por mês)
-- -------------------------------------------------------------
WITH ranked AS (
    SELECT
        s.name,
        s.unit,
        d.date,
        d.value,
        ROW_NUMBER() OVER (
            PARTITION BY d.series_code, DATE_TRUNC('month', d.date)
            ORDER BY d.date DESC
        ) AS rn
    FROM economic_data d
    JOIN economic_series s ON s.code = d.series_code
    WHERE d.date >= NOW() - INTERVAL '12 months'
)
SELECT name, unit, date, value
FROM ranked
WHERE rn = 1
ORDER BY name, date;


-- -------------------------------------------------------------
-- 2. IPCA acumulado nos últimos 12 meses
--    Fórmula: produtório de (1 + taxa/100) - 1
-- -------------------------------------------------------------
WITH ipca_12m AS (
    SELECT value
    FROM economic_data
    WHERE series_code = '433'
      AND date >= NOW() - INTERVAL '12 months'
)
SELECT
    ROUND(
        (EXP(SUM(LN(1 + value / 100))) - 1) * 100,
        2
    ) AS ipca_acumulado_12m
FROM ipca_12m;


-- -------------------------------------------------------------
-- 3. Variação mensal vs. média histórica (z-score do IPCA)
--    Mostra quais meses foram outliers
-- -------------------------------------------------------------
WITH stats AS (
    SELECT
        AVG(value)    AS media,
        STDDEV(value) AS desvio
    FROM economic_data
    WHERE series_code = '433'
),
ipca AS (
    SELECT date, value
    FROM economic_data
    WHERE series_code = '433'
    ORDER BY date DESC
    LIMIT 24
)
SELECT
    i.date,
    i.value,
    ROUND((i.value - s.media) / NULLIF(s.desvio, 0), 2) AS z_score,
    CASE
        WHEN (i.value - s.media) / NULLIF(s.desvio, 0) >  1.5 THEN 'Muito acima'
        WHEN (i.value - s.media) / NULLIF(s.desvio, 0) < -1.5 THEN 'Muito abaixo'
        ELSE 'Normal'
    END AS classificacao
FROM ipca i, stats s
ORDER BY i.date DESC;


-- -------------------------------------------------------------
-- 4. Correlação entre câmbio e IPCA (por mês)
--    Aproximação: se o dólar sobe, o IPCA costuma subir também?
-- -------------------------------------------------------------
WITH monthly_avg AS (
    SELECT
        DATE_TRUNC('month', date) AS mes,
        series_code,
        AVG(value) AS valor_medio
    FROM economic_data
    WHERE series_code IN ('433', '1')
      AND date >= NOW() - INTERVAL '3 years'
    GROUP BY mes, series_code
),
pivoted AS (
    SELECT
        mes,
        MAX(CASE WHEN series_code = '433' THEN valor_medio END) AS ipca,
        MAX(CASE WHEN series_code = '1'   THEN valor_medio END) AS cambio
    FROM monthly_avg
    GROUP BY mes
)
SELECT
    mes,
    ROUND(ipca::numeric, 4)   AS ipca,
    ROUND(cambio::numeric, 4) AS cambio_usd,
    -- variação mês a mês para cada série
    ROUND((ipca   - LAG(ipca)   OVER (ORDER BY mes)) / NULLIF(LAG(ipca)   OVER (ORDER BY mes), 0) * 100, 2) AS var_ipca_pct,
    ROUND((cambio - LAG(cambio) OVER (ORDER BY mes)) / NULLIF(LAG(cambio) OVER (ORDER BY mes), 0) * 100, 2) AS var_cambio_pct
FROM pivoted
ORDER BY mes DESC;


-- -------------------------------------------------------------
-- 5. Períodos de juros reais negativos
--    Juros real = Selic - IPCA acumulado
-- -------------------------------------------------------------
WITH monthly_selic AS (
    SELECT
        DATE_TRUNC('month', date) AS mes,
        AVG(value) AS selic_media
    FROM economic_data
    WHERE series_code = '432'
    GROUP BY mes
),
monthly_ipca AS (
    SELECT
        DATE_TRUNC('month', date) AS mes,
        value AS ipca
    FROM economic_data
    WHERE series_code = '433'
),
combined AS (
    SELECT
        s.mes,
        s.selic_media,
        i.ipca,
        s.selic_media - i.ipca * 12 AS juro_real_anualizado
    FROM monthly_selic s
    JOIN monthly_ipca i ON i.mes = s.mes
)
SELECT
    mes,
    ROUND(selic_media, 2)           AS selic_pct,
    ROUND(ipca, 2)                  AS ipca_pct,
    ROUND(juro_real_anualizado, 2)  AS juro_real,
    CASE
        WHEN juro_real_anualizado < 0 THEN '🔴 Negativo'
        ELSE '🟢 Positivo'
    END AS situacao
FROM combined
ORDER BY mes DESC
LIMIT 36;