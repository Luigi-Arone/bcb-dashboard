"""
Dashboard Econômico Brasileiro
Rode com: streamlit run dashboard/app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.analysis.queries import (
    get_latest_values,
    get_series_history,
    get_ipca_acumulado_12m,
    get_correlation_cambio_ipca,
    get_juros_reais,
)

# ── Tema e configuração ───────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Econômico BR",
    page_icon="📊",
    layout="wide",
)

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#1a1a2e",
    font=dict(color="#e0e0e0", family="monospace"),
    xaxis=dict(gridcolor="#2a2a4a", linecolor="#3a3a5a"),
    yaxis=dict(gridcolor="#2a2a4a", linecolor="#3a3a5a"),
    margin=dict(l=40, r=20, t=40, b=40),
)

COLORS = {
    "433":   "#00d4aa",  # IPCA — verde-água
    "432":   "#f0a500",  # Selic — âmbar
    "1":     "#4fc3f7",  # Câmbio — azul claro
    "24369": "#f06292",  # Desemprego — rosa
    "neg":   "#ef5350",  # juro real negativo
    "pos":   "#00d4aa",  # juro real positivo
}

FILL_COLORS = {
    "433":   "rgba(0, 212, 170, 0.08)",
    "432":   "rgba(240, 165, 0, 0.08)",
    "1":     "rgba(79, 195, 247, 0.08)",
    "24369": "rgba(240, 98, 146, 0.08)",
}


st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0f0f1a; }
    [data-testid="stSidebar"]          { background-color: #12122a; }
    [data-testid="metric-container"]   { background-color: #1a1a2e; border-radius: 12px; padding: 16px; border: 1px solid #2a2a4a; }
    h1, h2, h3                         { color: #e0e0e0 !important; }
    .stTabs [data-baseweb="tab"]       { color: #a0a0c0; }
    .stTabs [aria-selected="true"]     { color: #00d4aa !important; border-bottom-color: #00d4aa !important; }
    hr                                 { border-color: #2a2a4a; }
</style>
""", unsafe_allow_html=True)

# ── Cabeçalho ─────────────────────────────────────────────────
st.markdown("## 📊 Dashboard Econômico Brasileiro")
st.caption("Fonte: Banco Central do Brasil — API pública SGS")
st.divider()

# ── KPIs ──────────────────────────────────────────────────────
latest  = get_latest_values()
ipca_12m = get_ipca_acumulado_12m()

kpi_cols = st.columns(5)
for i, row in latest.iterrows():
    kpi_cols[i].metric(
        label=f"{row['name']}",
        value=f"{float(row['value']):.2f} {row['unit']}",
        delta=row["date"].strftime("%b/%Y"),
    )
kpi_cols[4].metric("IPCA acum. 12m", f"{ipca_12m:.2f}%")

st.divider()

# ── Históricos lado a lado ────────────────────────────────────
st.markdown("### Histórico dos indicadores")

col_left, col_right = st.columns(2)

series_map = {
    "IPCA":        ("433", "% ao mês"),
    "Selic":       ("432", "% ao ano"),
    "Câmbio USD":  ("1",   "R$"),
    "Desemprego":  ("24369", "% da PEA"),
}

items = list(series_map.items())

for idx, col in enumerate([col_left, col_right, col_left, col_right]):
    name, (code, unit) = items[idx]
    with col:
        months = st.slider(f"{name}", 12, 180, 60, key=f"slider_{code}")
        df = get_series_history(code, months)
        if df.empty:
            st.warning("Sem dados. Rode o coletor primeiro.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["value"],
                mode="lines",
                line=dict(color=COLORS[code], width=2),
                fill="tozeroy",
                fillcolor=FILL_COLORS[code],
                name=name,
            ))
            fig.update_layout(
                **PLOTLY_THEME,
                title=dict(text=f"{name} ({unit})", font=dict(size=14, color="#a0a0c0")),
                showlegend=False,
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Câmbio vs IPCA ────────────────────────────────────────────
st.markdown("### Variação mensal: Câmbio USD × IPCA")

df_corr = get_correlation_cambio_ipca(years=5)
if not df_corr.empty:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_corr["mes"], y=df_corr["var_ipca_pct"],
        name="Var. IPCA (%)", marker_color=COLORS["433"], opacity=0.85,
    ))
    fig2.add_trace(go.Bar(
        x=df_corr["mes"], y=df_corr["var_cambio_pct"],
        name="Var. Câmbio (%)", marker_color=COLORS["1"], opacity=0.85,
    ))
    fig2.update_layout(
        **PLOTLY_THEME,
        barmode="group",
        height=340,
        legend=dict(orientation="h", y=1.1, x=0),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Juros reais ───────────────────────────────────────────────
st.markdown("### Juros reais (Selic − IPCA anualizado)")
st.caption("Abaixo de zero: inflação corroeu os juros nominais.")

df_jr = get_juros_reais(months=36)
if not df_jr.empty:
    colors_jr = [COLORS["neg"] if v < 0 else COLORS["pos"] for v in df_jr["juro_real"]]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df_jr["mes"], y=df_jr["selic_pct"],
        name="Selic (% a.a.)",
        mode="lines",
        line=dict(color=COLORS["432"], width=2, dash="dot"),
    ))
    fig3.add_trace(go.Bar(
        x=df_jr["mes"], y=df_jr["juro_real"],
        name="Juro real",
        marker_color=colors_jr,
        opacity=0.85,
    ))
    fig3.add_hline(
        y=0,
        line_dash="dash",
        line_color="#555577",
        annotation_text="Juro real = 0",
        annotation_font_color="#a0a0c0",
    )
    fig3.update_layout(
        **PLOTLY_THEME,
        height=360,
        legend=dict(orientation="h", y=1.1, x=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption("Dados coletados via API pública do Banco Central do Brasil (SGS). Atualização manual via `python -m src.collectors.bcb`.")