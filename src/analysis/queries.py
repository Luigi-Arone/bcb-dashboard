"""
Funções que executam as queries analíticas e retornam DataFrames
prontos para o Streamlit/Plotly consumir.
"""

import streamlit as st

import pandas as pd
from src.db.connection import get_dict_connection


def get_series_history(series_code: str, months: int = 60) -> pd.DataFrame:
    """Retorna histórico de uma série nos últimos N meses."""
    sql = """
        SELECT d.date, d.value, s.name, s.unit
        FROM economic_data d
        JOIN economic_series s ON s.code = d.series_code
        WHERE d.series_code = %s
          AND d.date >= NOW() - INTERVAL '%s months'
        ORDER BY d.date
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (series_code, months))
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])


def get_ipca_acumulado_12m() -> float:
    """IPCA acumulado nos últimos 12 meses (produtório das taxas mensais)."""
    sql = """
        SELECT ROUND(
            (EXP(SUM(LN(1 + value / 100))) - 1) * 100, 2
        ) AS acumulado
        FROM economic_data
        WHERE series_code = '433'
          AND date >= NOW() - INTERVAL '12 months'
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            return float(row["acumulado"]) if row["acumulado"] else 0.0


def get_latest_values() -> pd.DataFrame:
    sql = """
        WITH ranked AS (
            SELECT
                s.name,
                s.unit,
                d.date,
                d.value,
                ROW_NUMBER() OVER (
                    PARTITION BY d.series_code
                    ORDER BY d.date DESC
                ) AS rn
            FROM economic_data d
            JOIN economic_series s ON s.code = d.series_code
        )
        SELECT name, unit, date, value
        FROM ranked
        WHERE rn = 1
        ORDER BY name
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])


def get_correlation_cambio_ipca(years: int = 5) -> pd.DataFrame:
    """
    Média mensal do câmbio e do IPCA lado a lado,
    com variação percentual mês a mês (window function).
    """
    sql = """
        WITH monthly_avg AS (
            SELECT
                DATE_TRUNC('month', date) AS mes,
                series_code,
                AVG(value) AS valor_medio
            FROM economic_data
            WHERE series_code IN ('433', '1')
              AND date >= NOW() - INTERVAL '%s years'
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
            ROUND(
                (ipca - LAG(ipca) OVER (ORDER BY mes))
                / NULLIF(LAG(ipca) OVER (ORDER BY mes), 0) * 100,
            2) AS var_ipca_pct,
            ROUND(
                (cambio - LAG(cambio) OVER (ORDER BY mes))
                / NULLIF(LAG(cambio) OVER (ORDER BY mes), 0) * 100,
            2) AS var_cambio_pct
        FROM pivoted
        ORDER BY mes
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql % years)
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])


def get_juros_reais(months: int = 36) -> pd.DataFrame:
    """Selic vs IPCA anualizado — identifica períodos de juro real negativo."""
    sql = """
        WITH monthly_selic AS (
            SELECT DATE_TRUNC('month', date) AS mes, AVG(value) AS selic
            FROM economic_data
            WHERE series_code = '432'
            GROUP BY mes
        ),
        monthly_ipca AS (
            SELECT DATE_TRUNC('month', date) AS mes, value AS ipca
            FROM economic_data
            WHERE series_code = '433'
        )
        SELECT
            s.mes,
            ROUND(s.selic, 2)                        AS selic_pct,
            ROUND(i.ipca, 2)                         AS ipca_mensal,
            ROUND(s.selic - i.ipca * 12, 2)          AS juro_real
        FROM monthly_selic s
        JOIN monthly_ipca i ON i.mes = s.mes
        WHERE s.mes >= NOW() - INTERVAL '%s months'
        ORDER BY s.mes
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql % months)
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])
        

@st.cache_data(ttl=3600)
def get_months_available(series_code: str) -> int:
    """Retorna quantos meses de dados existem para uma série."""
    sql = """
        SELECT
        (DATE_PART('year', MAX(date)) - DATE_PART('year', MIN(date))) * 12
        + (DATE_PART('month', MAX(date)) - DATE_PART('month', MIN(date)))
        AS meses
        FROM economic_data
        WHERE series_code = %s
        """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (series_code,))
            row = cur.fetchone()
            return int(row["meses"]) if row["meses"] else 12