"""
Funções que executam as queries analíticas e retornam DataFrames
prontos para o Streamlit/Plotly consumir.
"""

import requests
import streamlit as st
import pandas as pd
from datetime import date
from src.db.connection import get_dict_connection


@st.cache_data(ttl=3600)
def get_ipca_acumulado_12m() -> float:
    """IPCA acumulado nos últimos 12 meses (produtório das taxas mensais)."""
    sql = """
        SELECT ROUND(
        (EXP(SUM(LN(1 + value / 100))) - 1) * 100, 2
        ) AS acumulado
        FROM (
        SELECT DISTINCT ON (DATE_TRUNC('month', date)) value
        FROM economic_data
        WHERE series_code = '433'
        AND date >= NOW() - INTERVAL '12 months'
        ORDER BY DATE_TRUNC('month', date), date DESC
        ) AS ipca_mensal
        """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            return float(row["acumulado"]) if row["acumulado"] else 0.0


@st.cache_data(ttl=3600)
def get_latest_values() -> pd.DataFrame:
    """Último valor disponível de cada indicador."""
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


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
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
            ROUND(s.selic, 2)               AS selic_pct,
            ROUND(i.ipca, 2)                AS ipca_mensal,
            ROUND(
            ((1 + s.selic/100) / (1 + (i.ipca * 12)/100) - 1) * 100,
            2) AS juro_real
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
def get_selic_mensal() -> pd.DataFrame:
    """Retorna média mensal da Selic histórica."""
    sql = """
        SELECT DATE_TRUNC('month', date) AS mes, AVG(value) AS selic
        FROM economic_data
        WHERE series_code = '432'
        GROUP BY mes
        ORDER BY mes
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            df = pd.DataFrame([dict(r) for r in rows])
            df["mes"] = pd.to_datetime(df["mes"], utc=True).dt.tz_convert(None)
            return df


@st.cache_data(ttl=3600)
def get_cdi_historico() -> pd.DataFrame:
    """Retorna CDI histórico mensal anualizado (252 dias úteis)."""
    sql = """
        SELECT DATE_TRUNC('month', date) AS ds, AVG(value) * 252 AS cdi
        FROM economic_data
        WHERE series_code = '12'
        GROUP BY ds
        ORDER BY ds
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            df = pd.DataFrame([dict(r) for r in rows])
            df["ds"] = pd.to_datetime(df["ds"], utc=True).dt.tz_convert(None)
            return df


@st.cache_data(ttl=3600)
def get_expectativa_focus(meetings_ahead: int = 6) -> pd.DataFrame:
    """
    Busca expectativas do mercado para a Selic por reunião do Copom via API Focus (BCB).
    Retorna a mediana mais recente para cada reunião futura.
    """
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
        "ExpectativasMercadoSelic"
        "?$filter=Indicador%20eq%20'Selic'"
        "&$orderby=Data%20desc"
        "&$top=200"
        "&$format=json"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    dados = response.json()["value"]

    df = pd.DataFrame(dados)
    df["Data"] = pd.to_datetime(df["Data"])

    # Pega só baseCalculo=1 (suavizado) e a coleta mais recente por reunião
    df = df[df["baseCalculo"] == 1]
    df = df.sort_values("Data", ascending=False)
    df = df.drop_duplicates(subset="Reuniao", keep="first")

    # Ordena reuniões cronologicamente: R1/2026, R2/2026, ..., R8/2026, R1/2027...
    df[["num", "ano"]] = df["Reuniao"].str.extract(r"R(\d+)/(\d+)").astype(int)
    df = df.sort_values(["ano", "num"]).head(meetings_ahead)

    # Data aproximada de cada reunião (para o eixo X do gráfico)
    df["ds"] = pd.to_datetime(df["ano"].astype(str) + "-01-01") + pd.to_timedelta(
        ((df["num"] - 1) * 45), unit="D"
    )

    return df[["ds", "Reuniao", "Mediana", "Minimo", "Maximo"]].rename(
        columns={"Mediana": "selic_esperada"}
    )


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