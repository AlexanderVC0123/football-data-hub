import os
import sys
import base64

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics.dashboard_metrics import calculate_competition_kpis
from app.analytics.match_analysis import compare_teams, estimate_match_probabilities
from app.config import manual_sync_enabled
from app.database.connection import execute_schema
from app.database.read_queries import (
    load_competitions,
    load_last_sync_run,
    load_matches,
    load_matches_by_team,
    load_standings,
    load_teams,
)
from app.services.import_service import sync_competition_data
from pathlib import Path
from auth_page import inicializar_sesion, mostrar_login_header, mostrar_usuario_header
from datetime import datetime, timezone


st.set_page_config(
    page_title="Football Data Hub",
    page_icon="./assets/icons/fdh_icon.ico",
    layout="wide",
)

# Asegura tablas nuevas como sync_runs antes de leer datos para construir la UI.
if "schema_checked" not in st.session_state:
    execute_schema()
    st.session_state.schema_checked = True


def apply_page_styles():
    st.markdown(
        """
        <style>
        /* Quitamos padding superior excesivo de Streamlit */
        .block-container {
            padding-top: 1.2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* === NAVBAR COMO BLOQUE ÚNICO === */
        .st-key-fdh_topbar {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 12px 20px;
            margin-bottom: 16px;
        }

        .st-key-fdh_topbar div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        
        .fdh-navbar {
            background: transparent;
            border: none;
            padding: 0;
            min-height: 0;
        }

        .fdh-brand img {
            width: 42px;
            height: 42px;
            object-fit: contain;
        }

        .fdh-brand-title {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.1;
        }

        .fdh-brand-subtitle {
            color: #94a3b8;
            font-size: 0.75rem;
            margin: 2px 0 0 0;
        }

        .st-key-fdh_topbar div[data-testid="stButton"] button {
            border-radius: 10px;
            border: 1px solid #1e293b;
            background: #111827;
            color: #e5e7eb;
            font-weight: 600;
            height: 38px;
            font-size: 0.88rem;
        }

        .st-key-fdh_topbar div[data-testid="stButton"] button:hover {
            border-color: #38bdf8;
            color: #ffffff;
            background: #172033;
        }

        .st-key-fdh_topbar div[data-testid="stPopover"] button {
            border-radius: 10px;
            border: 1px solid #1e293b;
            background: #111827;
            color: #e5e7eb;
            font-weight: 600;
            height: 38px;
            font-size: 0.88rem;
            width: 100%;
        }

        .st-key-fdh_topbar div[data-testid="stPopover"] button:hover {
            border-color: #38bdf8;
            background: #172033;
        }

        /* === DENTRO DEL POPOVER === */
        div[data-testid="stForm"] {
            background: transparent;
            border: none;
            padding: 0;
            box-shadow: none;
        }

        div[data-testid="stForm"] input {
            background: #111827;
            color: #f8fafc;
            border-radius: 8px;
            height: 38px;
        }

        .fdh-user-box {
            background: transparent;
            border: none;
            padding: 0;
            min-height: 0;
            margin-bottom: 10px;
        }

        .fdh-user-box h3 {
            margin: 0 0 4px 0;
            font-size: 0.85rem;
            color: #f8fafc;
        }

        .fdh-user-email {
            font-size: 0.8rem;
            color: #cbd5e1;
            word-break: break-word;
        }

        /* === LÍNEA DE SINCRONIZACIÓN === */
        .fdh-sync-line {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #94a3b8;
            font-size: 0.82rem;
            padding: 4px 2px;
            margin: 4px 0 16px 0;
        }

        .fdh-sync-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .fdh-sync-dot-ok {
            background: #22c55e;
            box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
        }

        .fdh-sync-dot-err {
            background: #ef4444;
            box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
        }

        .fdh-sync-dot-gray {
            background: #64748b;
        }

        /* === TABLAS HTML CUSTOM === */
        .fdh-table {
            width: 100%;
            border-collapse: collapse;
            background: #0b1220;
            color: #e5e7eb;
            border: 1px solid #1e293b;
            border-radius: 10px;
            overflow: hidden;
            font-size: 0.9rem;
        }

        .fdh-table th {
            background: #111827;
            color: #93c5fd;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-table td {
            padding: 9px 12px;
            border-bottom: 1px solid #1f2937;
        }

        /* === ESTADO VACÍO (cuando faltan datos) === */
        .fdh-empty {
            border: 1px solid #1e293b;
            background: #0b1220;
            padding: 28px;
            border-radius: 12px;
            color: #cbd5e1;
        }

        .fdh-empty h3 {
            color: #f8fafc;
            margin: 0 0 8px 0;
        }

        /* === MÉTRICAS NATIVAS DE STREAMLIT === */
        div[data-testid="stMetric"] {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 16px 18px;
        }

        div[data-testid="stMetricLabel"] {
            color: #94a3b8;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 500;
        }

        div[data-testid="stMetricLabel"] p {
            color: #94a3b8 !important;
        }

        div[data-testid="stMetricValue"] {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 4px;
        }

        div[data-testid="stMetricDelta"] {
            font-size: 0.78rem;
            font-weight: 600;
        }

        /* Caption debajo de st.metric: contexto de la comparación */
        div[data-testid="stCaptionContainer"] {
            color: #94a3b8;
            font-size: 0.75rem;
            margin-top: -8px;
            line-height: 1.4;
        }

        /* === TARJETAS DE PARTIDO === */
        .fdh-matches-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 20px;
            height: 100%;
        }

        .fdh-matches-header {
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-matches-header h3 {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin: 0;
        }

        .fdh-matches-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .fdh-match-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 12px 14px;
            transition: border-color 150ms ease;
        }

        .fdh-match-card:hover {
            border-color: #334155;
        }

        .fdh-match-jornada {
            color: #64748b;
            font-size: 0.7rem;
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-match-body {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            gap: 12px;
        }

        .fdh-match-team {
            font-size: 0.9rem;
            font-weight: 600;
        }

        .fdh-match-team:first-of-type {
            text-align: right;
        }

        .fdh-match-team:last-of-type {
            text-align: left;
        }

        .fdh-match-team-winner { color: #f8fafc; }
        .fdh-match-team-loser { color: #64748b; }
        .fdh-match-team-draw { color: #cbd5e1; }
        .fdh-match-team-pending { color: #cbd5e1; }

        .fdh-match-score {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.2rem;
            font-weight: 800;
            padding: 0 10px;
        }

        .fdh-match-score-winner { color: #f8fafc; }
        .fdh-match-score-loser { color: #64748b; }
        .fdh-match-score-draw { color: #cbd5e1; }
        .fdh-match-score-sep { color: #475569; }

        .fdh-match-time {
            color: #38bdf8;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 0 14px;
            white-space: nowrap;
        }

        .fdh-match-meta {
            color: #64748b;
            font-size: 0.7rem;
            margin-top: 8px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-match-meta-pending {
            color: #38bdf8;
        }

        .fdh-matches-empty {
            color: #64748b;
            font-size: 0.88rem;
            padding: 24px 12px;
            text-align: center;
        }

        /* === MINI TABLA TOP + BOTTOM === */
        .fdh-mini-table {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 20px;
        }

        .fdh-mini-header {
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-mini-header h3 {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin: 0 0 4px 0;
        }

        .fdh-mini-header p {
            color: #94a3b8;
            font-size: 0.78rem;
            margin: 0;
        }

        .fdh-mini-section {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .fdh-mini-label {
            color: #64748b;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
            font-weight: 600;
        }

        .fdh-mini-divider {
            height: 1px;
            background: #1e293b;
            margin: 14px 0;
        }

        .fdh-mini-row {
            display: grid;
            grid-template-columns: 28px 1fr auto auto;
            align-items: center;
            gap: 12px;
            padding: 7px 10px;
            border-radius: 6px;
            border-left: 3px solid transparent;
        }

        .fdh-mini-champions { border-left-color: #22c55e; background: rgba(34, 197, 94, 0.04); }
        .fdh-mini-europa { border-left-color: #3b82f6; background: rgba(59, 130, 246, 0.04); }
        .fdh-mini-descenso { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.04); }

        .fdh-mini-pos {
            color: #64748b;
            font-size: 0.8rem;
            font-weight: 700;
            text-align: right;
        }

        .fdh-mini-team {
            color: #e5e7eb;
            font-size: 0.85rem;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .fdh-mini-played {
            color: #64748b;
            font-size: 0.75rem;
        }

        .fdh-mini-points {
            color: #f8fafc;
            font-size: 0.85rem;
            font-weight: 700;
            min-width: 50px;
            text-align: right;
        }

        /* === LANDING DE LOGIN === */
        .fdh-landing {
            max-width: 1100px;
            margin: 30px auto 60px auto;
            padding: 0 20px;
        }

        .fdh-landing-hero {
            text-align: center;
            padding: 50px 20px 40px 20px;
        }

        .fdh-landing-badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.10);
            border: 1px solid rgba(56, 189, 248, 0.25);
            color: #38bdf8;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 999px;
            margin-bottom: 20px;
        }

        .fdh-landing-title {
            color: #f8fafc;
            font-size: 2.4rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0 auto 18px auto;
            max-width: 720px;
            letter-spacing: -0.01em;
        }

        .fdh-landing-subtitle {
            color: #cbd5e1;
            font-size: 1.08rem;
            line-height: 1.55;
            max-width: 640px;
            margin: 0 auto 28px auto;
        }

        .fdh-landing-hint {
            color: #94a3b8;
            font-size: 0.92rem;
            margin: 0;
        }

        .fdh-landing-hint strong {
            color: #38bdf8;
            font-weight: 600;
        }

        .fdh-landing-features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px;
            margin-top: 30px;
        }

        .fdh-feature {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 22px 20px;
            transition: border-color 150ms ease, transform 150ms ease;
        }

        .fdh-feature:hover {
            border-color: #334155;
            transform: translateY(-2px);
        }

        .fdh-feature-icon {
            font-size: 1.6rem;
            margin-bottom: 12px;
        }

        .fdh-feature-title {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .fdh-feature-desc {
            color: #94a3b8;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        @media (max-width: 900px) {
            .fdh-landing-features {
                grid-template-columns: 1fr;
            }
            .fdh-landing-title {
                font-size: 1.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str):
    st.markdown(
        f"""
        <div class="fdh-empty">
            <h3>{title}</h3>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_login_landing():
    """Landing que se muestra cuando el usuario no ha iniciado sesión."""
    st.markdown(
        """
        <div class="fdh-landing">
            <div class="fdh-landing-hero">
                <div class="fdh-landing-badge">⚽ Football Data Hub</div>
                <h1 class="fdh-landing-title">
                    Análisis y predicciones de las cinco grandes ligas europeas
                </h1>
                <p class="fdh-landing-subtitle">
                    Datos en tiempo real, estadísticas avanzadas y modelos de predicción
                    sobre LaLiga, Premier League, Serie A, Bundesliga y Ligue 1.
                </p>
                <p class="fdh-landing-hint">
                    Pulsa <strong>Acceder</strong> en la esquina superior derecha para iniciar sesión.
                </p>
            </div>
            <div class="fdh-landing-features">
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">📊</div>
                    <div class="fdh-feature-title">Estadísticas actualizadas</div>
                    <div class="fdh-feature-desc">
                        Sincronización automática cada 6 horas desde football-data.org.
                        Clasificaciones, goles, defensas y rendimiento al día.
                    </div>
                </div>
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">⚖️</div>
                    <div class="fdh-feature-title">Comparador de equipos</div>
                    <div class="fdh-feature-desc">
                        Enfrenta a cualquier pareja de equipos de la misma competición
                        y compara métricas clave de rendimiento.
                    </div>
                </div>
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">🎯</div>
                    <div class="fdh-feature-title">Predicciones por modelo</div>
                    <div class="fdh-feature-desc">
                        Probabilidades 1X2, goles esperados y marcadores más probables
                        calculados con un modelo de Poisson sobre los últimos partidos.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    

def render_brand():
    BASE_DIR = Path(__file__).resolve().parent.parent
    logo_path = BASE_DIR / "assets" / "branding" / "fdh_logo_web_512.webp"
    logo_base64 = image_to_base64(logo_path)
    

    st.markdown(
        f"""
        <div class="fdh-navbar">
            <div class="fdh-brand">
                <img src="data:image/webp;base64,{logo_base64}" alt="FDH logo">
                <div>
                    <p class="fdh-brand-title">Football Data Hub</p>
                    <p class="fdh-brand-subtitle">Football analytics dashboard</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def cambiar_pagina(nombre_pagina):
    st.session_state.pagina_actual = nombre_pagina

def render_navigation():
    if "pagina_actual" not in st.session_state:
        st.session_state.pagina_actual = "Resumen"

    paginas = [
        "Resumen",
        "Clasificación",
        "Partidos",
        "Equipo",
        "Enfrentamientos"
    ]

    cols = st.columns(len(paginas))

    for col, pagina in zip(cols, paginas):
        with col:
            if st.button(pagina, key=f"nav_{pagina}", use_container_width=True):
                cambiar_pagina(pagina)
        
    return st.session_state.pagina_actual

def render_topbar():

    inicializar_sesion()

    with st.container(key="fdh_topbar"):

        col_brand, col_nav, col_user = st.columns([2,4, 1.2], gap="small", vertical_alignment="center",)

        with col_brand:
            render_brand()
        
        with col_nav:
            selected_page = render_navigation()

        with col_user:
            if st.session_state.logueado:
                mostrar_usuario_header()
            else:
                mostrar_login_header()
    return selected_page

def humanize_time_ago(timestamp):
    "Convierte un timestamp en tiempo legible como: 'Hace X tiempo'."
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z","+00:00"))
        except ValueError:
            return "Fecha desconocida"
    
    # pandas Timestamp también funciona; lo convertimos a datetime si hace falta
    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()
    
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - timestamp
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "hace unos segundos"
    if seconds < 3600:
        minutos = seconds // 60
        return f"hace {minutos} minuto{'s' if minutos != 1 else ''}"
    if seconds < 86400:
        horas = seconds // 3600
        return f"hace {horas} hora{'s' if horas != 1 else ''}"
    dias = seconds // 86400
    return f"hace {dias} día{'s' if dias != 1 else ''}" 

def render_sync_status(last_sync_df: pd.DataFrame):
    if last_sync_df.empty:
        st.markdown(
            '<div class="fdh-sync-line>'
            '<span class="fdh-sync-dot fdh-sync-dot-gray"></span>'
            'Sincronizaciones registradas'
            '</div>',
            unsafe_allow_html=True
        )
        return
    last_sync = last_sync_df.iloc[0]
    ok = last_sync["status"] == "SUCCESS"
    when = humanize_time_ago(last_sync["finished_at"])

    dot_class = "fdh-sync-dot-ok" if ok else "fdh-sync-dot-err"
    label = "correcta" if ok else "fallida"

    st.markdown(
        f'<div class="fdh-status">'
        f'<span class="fdh-sync-dot{dot_class}"></span>'
        f'Última actualización · {when} · {label}'
        f'</div>'
        , unsafe_allow_html=True
    
    )


def render_dark_table(df: pd.DataFrame, max_rows: int | None = None):
    display_df = df.head(max_rows) if max_rows else df
    html = display_df.to_html(index=False, classes="fdh-table", border=0, escape=True)
    st.markdown(html, unsafe_allow_html=True)


def configure_plot(fig, height: int = 420, show_colorscale: bool = False):
    """
    Aplica el tema visual unificado a un gráfico de Plotly.
    
    Args:
        fig: figura de Plotly
        height: alto en píxeles
        show_colorscale: si True, muestra la barra de color lateral
                         (útil solo en scatters donde el color codifica una dimensión extra)
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font_color="#cbd5e1",
        font_family="Source Sans Pro, system-ui, sans-serif",
        font_size=12,
        height=height,
        margin=dict(l=50, r=20, t=50, b=50),
        title=dict(
            font=dict(color="#f8fafc", size=14, family="Source Sans Pro, system-ui, sans-serif"),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#1e293b",
            linecolor="#1e293b",
            tickfont=dict(color="#94a3b8", size=11),
            title_font=dict(color="#cbd5e1", size=12),
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#1e293b",
            linecolor="#1e293b",
            tickfont=dict(color="#94a3b8", size=11),
            title_font=dict(color="#cbd5e1", size=12),
        ),
        hoverlabel=dict(
            bgcolor="#111827",
            bordercolor="#334155",
            font=dict(color="#f8fafc", family="Source Sans Pro, system-ui, sans-serif", size=12),
        ),
        coloraxis_showscale=show_colorscale,
        showlegend=False,
    )
    return fig


apply_page_styles()

def get_team_recent_form(team_name: str, matches_df: pd.DataFrame, n: int=5):
    """
    Devuelve la lista de los N últimos resultados(más reciente primero)
    Cada resultado es 'W', 'D', o 'L'
    """
    if matches_df.empty:
        return []
    
    finished = matches_df[matches_df["status"] == "FINISHED"].copy()
    if finished.empty:
        return []
    
    played = finished[
        (finished["home_team"] == team_name) | (finished["away_team"] == team_name)
    ].copy()

    if played.empty:
        return []
    
    played["utc_date"] = pd.to_datetime(played["utc_date"], errors="coerce")
    played = played.sort_values("utc_date", ascending=False).head(n)

    results = []
    for _, match in played.iterrows():
        is_home = match["home_team"] == team_name
        team_goals = match["home_score"] if is_home else match["away_score"]
        opp_goals = match["away_score"] if is_home else match["home_score"]

        if pd.isna(team_goals) or pd.isna(opp_goals):
            continue
        if team_goals > opp_goals:
            results.append("W")
        if team_goals < opp_goals:
            results.append("L")
        else:
            results.append("D")
    return results

def style_standings_table(df: pd.DataFrame):
    """Aplica color de fondo según zona de la clasificación."""
    total_teams = len(df)
    descenso_from = total_teams - 2

    def color_row(row):
        pos = row["Posición"]
        if pos <= 4:
            return ["background-color: rgba(34, 197, 94, 0.08)"] * len(row)
        if pos <=6:
            return ["background-color: rgba(59, 130, 246, 0.08)"] * len(row)
        if pos >= descenso_from:
            return ["background-color: rgba(239, 68, 68, 0.08)"] * len(row)
        return [""] * len(row)
    
    styled = df.style.apply(color_row, axis=1)
    styled = styled.set_properties(**{
        "color": "#e5e7eb",
        "font-size": "0.88rem",
    })

    return styled

def render_match_card(home_team, away_team, home_score, away_score,
                      match_date, status, matchday=None):
    """
    Renderiza una tarjeta de partido individual estilo Sofascore.
    Marcador centrado y grande si está finalizado; hora/fecha si está pendiente.
    """

    is_finished = status == "FINISHED"
    if is_finished and pd.notna(home_score) and pd.notna(away_score):
        #Determinar el ganador para resaltar
        if home_score > away_score:
            home_class, away_class = "fdh-match-team-winner", "fdh-match-team-loser"
        elif home_score < away_score:
            home_class, away_class = "fdh-match-team-loser", "fdh-match-team-winner"
        else:
            home_class, away_class = "fdh-match-team-draw"
        
        score_html = (
            f'<div class="fdh-match-score">'
            f'<span class="{home_class.replace("team-", "score-")}">{int(home_score)}</span>'
            f'<span class="fdh-match-score-sep">-</span>'
            f'<span class="{away_class.replace("team-", "score-")}">{int(away_score)}</span>'
            f'</div>'
        )
        meta_html = '<div class="fdh-match-meta">Finalizado</div>'
    else:
        home_class = away_class = "fdh-match-team-pending"
        try:
            date_str = pd.to_datetime(match_date).strftime("%d %b · %H:%M")
        except Exception:
            date_str = ""
        score_html = f'<div class="fdh-match-time">{date_str}</div>'
        meta_html = '<div class="fdh-match-meta fdh-match-meta-pending">Pendiente</div>'
    
    matchday_html = (
        f'<div class="fdh-match-jornada">J{int(matchday)}</div>' 
        if matchday is not None and pd.notna(matchday) else ""
    )
    
    return (
        f'<div class="fdh-match-card">'
        f'{matchday_html}'
        f'<div class="fdh-match-body">'
        f'<div class="fdh-match-team {home_class}">{home_team}</div>'
        f'{score_html}'
        f'<div class="fdh-match-team {away_class}">{away_team}</div>'
        f'</div>'
        f'{meta_html}'
        f'</div>'
    )


def render_matches_list(matches_df: pd.DataFrame, title: str, empty_text: str, limit: int = 6):
    """Renderiza una lista de partidos con título y estado vacío."""
    cards_html = ""
    if matches_df.empty:
        cards_html = f'<div class="fdh-matches-empty">{empty_text}</div>'
    else:
        for _, match in matches_df.head(limit).iterrows():
            cards_html += render_match_card(
                home_team=match["home_team"],
                away_team=match["away_team"],
                home_score=match.get("home_score"),
                away_score=match.get("away_score"),
                match_date=match["utc_date"],
                status=match["status"],
                matchday=match.get("matchday"),
            )

    block_html = (
        f'<div class="fdh-matches-block">'
        f'<div class="fdh-matches-header"><h3>{title}</h3></div>'
        f'<div class="fdh-matches-list">{cards_html}</div>'
        f'</div>'
    )
    
    st.markdown(block_html, unsafe_allow_html=True)

def render_top_bottom_table(standings_df: pd.DataFrame):
    """Muestra los 5 primeros y los 3 últimos de la clasificación."""
    if standings_df.empty:
        return
    
    sorted_df = standings_df.sort_values("position")
    top5 = sorted_df.head(5)
    bottom3 = sorted_df.tail(3)
    
    def row_html(row, zone_class=""):
        return (
            f'<div class="fdh-mini-row {zone_class}">'
            f'<span class="fdh-mini-pos">{int(row['position'])}</span>'
            f'<span class="fdh-mini-team">{row['team']}</span>'
            f'<span class="fdh-mini-played">{int(row['played_games'])} PJ</span>'
            f'<span class="fdh-mini-points">{int(row['points'])} pts</span>'
            f'</div>'
        )
    
    top_rows = ""
    for _, row in top5.iterrows():
        zone = "fdh-mini-champions" if row["position"] <= 4 else "fdh-mini-europa"
        top_rows += row_html(row, zone)
    
    bottom_rows = ""
    for _, row in bottom3.iterrows():
        bottom_rows += row_html(row, "fdh-mini-descenso")
    
    block_html = (
        f'<div class="fdh-mini-table">'
        f'<div class="fdh-mini-header">'
        f'<h3>Clasificación</h3>'
        f'<p>5 primeros y 3 últimos</p>'
        f'</div>'
        f'<div class="fdh-mini-section">'
        f'<div class="fdh-mini-label">Cabeza</div>'
        f'{top_rows}'
        f'</div>'
        f'<div class="fdh-mini-divider"></div>'
        f'<div class="fdh-mini-section">'
        f'<div class="fdh-mini-label">Cola</div>'
        f'{bottom_rows}'
        f'</div>'
        f'</div>'
    )
    st.markdown(block_html, unsafe_allow_html=True)

def format_standings_table(df: pd.DataFrame):
    return df.rename(
        columns={
            "position": "Posición",
            "team": "Equipo",
            "played_games": "Partidos",
            "won": "Victorias",
            "draw": "Empates",
            "lost": "Derrotas",
            "points": "Puntos",
            "goals_for": "Goles a favor",
            "goals_against": "Goles en contra",
            "goal_difference": "Diferencia de goles",
        }
    )


def format_matches_table(df: pd.DataFrame):
    return df.rename(
        columns={
            "matchday": "Jornada",
            "utc_date": "Fecha/Hora",
            "home_team": "Local",
            "away_team": "Visitante",
            "home_score": "Gol local",
            "away_score": "Gol visitante",
            "status": "Estado",
        }
    )


def load_combined_matches(competition_id: int, *team_names: str):
    frames = [
        load_matches_by_team(team_name, competition_id=competition_id)
        for team_name in team_names
        if team_name
    ]
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(
        subset=["matchday", "utc_date", "home_team", "away_team"],
        keep="first",
    )


def probability_chart(prediction: dict):
    labels = [
        prediction["home_team"],
        "Empate",
        prediction["away_team"],
    ]
    values = [
        prediction["home_win_probability"],
        prediction["draw_probability"],
        prediction["away_win_probability"],
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=["#1f7a4d", "#6b7280", "#2563eb"],
                text=[f"{value:.1f}%" for value in values],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title="Probabilidad estimada",
        yaxis_title="Probabilidad",
        xaxis_title="Resultado",
        yaxis_ticksuffix="%",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return configure_plot(fig, height=360)


selected_page = render_topbar()

if not st.session_state.logueado:
    render_login_landing()
    st.stop()

competitions_df = load_competitions()
if competitions_df.empty:
    render_empty_state(
        "Datos en preparación",
        "Todavía no hay competiciones cargadas. Cuando el proceso de sincronización termine, este panel mostrará las ligas disponibles automáticamente.",
    )
    st.stop()

competition_options = {
    f"{row['name']} ({row['code']})": {"id": int(row["id"]), "code": row["code"]}
    for _, row in competitions_df.iterrows()
}
selected_competition_label = st.selectbox("Competición", list(competition_options.keys()))
selected_competition = competition_options[selected_competition_label]
selected_competition_id = selected_competition["id"]
selected_competition_code = selected_competition["code"]

last_sync_df = load_last_sync_run(selected_competition_code)
render_sync_status(last_sync_df)

if manual_sync_enabled(): 
    with st.expander("Herramienta de mantenimiento"):
        if st.button("Actualizar competición desde API"):
        # La sincronización usa upserts: si el registro ya existe, se actualiza con
        # los datos nuevos de la API en vez de quedarse con informacion antigua.
            with st.spinner(f"Actualizando {selected_competition_code} desde la API..."):
                sync_competition_data(selected_competition_code)
            st.success("Datos actualizados correctamente.")
            st.rerun()

standings_df = load_standings(selected_competition_id)
teams_df = load_teams(selected_competition_id)
competition_matches_df = load_matches(selected_competition_id)
teams_list = teams_df["name"].tolist()

if standings_df.empty or not teams_list:
    render_empty_state(
        "Competición sin datos analíticos",
        "La competición existe en la base, pero aún no tiene clasificación o equipos asociados. El panel se completará después de la próxima sincronización.",
    )
    st.stop()

display_standings_df = format_standings_table(standings_df)
kpis = calculate_competition_kpis(standings_df, competition_matches_df)

#Dataframes precalculados que se usan en varias pestañas
finished_matches_df = competition_matches_df[
    competition_matches_df["status"] == "FINISHED"
].copy()
pending_matches_df = competition_matches_df[
    competition_matches_df["status"] != "FINISHED"
].copy()

if not finished_matches_df.empty:
    finished_matches_df["utc_date"] = pd.to_datetime(
        finished_matches_df["utc_date"], errors="coerce"
    )
if not pending_matches_df.empty:
    pending_matches_df["utc_date"] = pd.to_datetime(
        pending_matches_df["utc_date"], errors="coerce"
    )

if selected_page == "Resumen":
    # --- KPIs principales (lo que ya tienes) ---
    main_kpi_cols = st.columns(4)
    main_kpi_keys = ["leader", "top_attack", "best_defense", "goals_per_match"]
    
    for column, key in zip(main_kpi_cols, main_kpi_keys):
        item = kpis[key]
        with column:
            delta_val = item.get("delta_numeric")
            if delta_val is not None:
                st.metric(
                    label=item["label"],
                    value=item["value"],
                    delta=f"+{delta_val}" if delta_val > 0 else str(delta_val),
                )
                st.caption(item["detail"])
            else:
                st.metric(label=item["label"], value=item["value"])
                st.caption(item["detail"])
    
    with st.expander("Ver más indicadores"):
        secondary_kpi_cols = st.columns(4)
        secondary_kpi_keys = ["highest_scoring_match", "next_match", "completion_rate", "pending_matches"]
        
        for column, key in zip(secondary_kpi_cols, secondary_kpi_keys):
            item = kpis[key]
            with column:
                delta_val = item.get("delta_numeric")
                if delta_val is not None:
                    st.metric(
                        label=item["label"],
                        value=item["value"],
                        delta=f"+{delta_val}" if delta_val > 0 else str(delta_val),
                    )
                    st.caption(item["detail"])
                else:
                    st.metric(label=item["label"], value=item["value"])
                    st.caption(item["detail"])
    
    st.divider()
    
    # --- Resultados última jornada | Próximos partidos ---
    col_recent, col_upcoming = st.columns(2)
    
    with col_recent:
        # Última jornada con partidos finalizados
        if not finished_matches_df.empty:
            last_matchday = int(finished_matches_df["matchday"].max())
            recent_matches = finished_matches_df[
                finished_matches_df["matchday"] == last_matchday
            ].sort_values("utc_date", ascending=False)
            title = f"Última jornada · J{last_matchday}"
        else:
            recent_matches = pd.DataFrame()
            title = "Última jornada"
        
        render_matches_list(
            recent_matches,
            title=title,
            empty_text="No hay partidos finalizados todavía.",
            limit=6,
        )
    
    with col_upcoming:
        # Próximos partidos pendientes
        upcoming = pending_matches_df.sort_values("utc_date").head(6) \
            if not pending_matches_df.empty else pd.DataFrame()
        
        render_matches_list(
            upcoming,
            title="Próximos partidos",
            empty_text="No hay partidos programados.",
            limit=6,
        )
    
    st.divider()
    
    # --- Mini tabla top + bottom ---
    col_mini, col_charts = st.columns([1, 2])
    
    with col_mini:
        render_top_bottom_table(standings_df)
    
    with col_charts:
        # Aquí dejamos los 3 gráficos actuales en horizontal pequeño
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            attack_fig = px.bar(
                standings_df.sort_values("goals_for", ascending=False).head(6),
                x="team",
                y="goals_for",
                color="goals_for",
                title="Ataques más productivos",
                color_continuous_scale="Greens",
            )
            attack_fig.update_layout(xaxis_title="", yaxis_title="Goles")
            st.plotly_chart(configure_plot(attack_fig, height=320), width="stretch")
        
        with chart_col2:
            defense_fig = px.bar(
                standings_df.sort_values("goals_against", ascending=True).head(6),
                x="team",
                y="goals_against",
                color="goals_against",
                title="Defensas más sólidas",
                color_continuous_scale="Blues_r",
            )
            defense_fig.update_layout(xaxis_title="", yaxis_title="Encajados")
            st.plotly_chart(configure_plot(defense_fig, height=320), width="stretch")

elif selected_page == "Partidos":
    selected_team = st.selectbox("Equipo", teams_list, key="matches_team")
    matches_df = load_matches_by_team(selected_team, competition_id=selected_competition_id)
    display_matches_df = format_matches_table(matches_df)

    render_dark_table(display_matches_df)

    finished_matches = matches_df[matches_df["status"].eq("FINISHED")].copy()
    if not finished_matches.empty:
        finished_matches["total_goals"] = (
            finished_matches["home_score"].fillna(0) + finished_matches["away_score"].fillna(0)
        )
        fig = px.scatter(
            finished_matches,
            x="utc_date",
            y="total_goals",
            color="status",
            size="total_goals",
            hover_data=["home_team", "away_team", "home_score", "away_score"],
            title=f"Goles por partido - {selected_team}",
        )
        fig.update_layout(xaxis_title="Fecha", yaxis_title="Goles")
        st.plotly_chart(configure_plot(fig, height=420), width="stretch")

elif selected_page == "Comparador":
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Equipo A", teams_list, key="compare_home")
    with col2:
        away_team = st.selectbox("Equipo B", teams_list, index=min(1, len(teams_list) - 1), key="compare_away")

    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes.")
    else:
        comparison_matches = load_combined_matches(selected_competition_id, home_team, away_team)
        comparison_df = compare_teams(standings_df, comparison_matches, home_team, away_team)

        fig = px.bar(
            comparison_df,
            x="metric",
            y="value",
            color="team",
            barmode="group",
            title="Comparativa de rendimiento",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Valor", showlegend=True)
        st.plotly_chart(configure_plot(fig, height=520), width="stretch")
        render_dark_table(comparison_df)

elif selected_page == "Predicción":
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Local", teams_list, key="prediction_home")
    with col2:
        away_team = st.selectbox("Visitante", teams_list, index=min(1, len(teams_list) - 1), key="prediction_away")

    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes.")
    else:
        prediction_matches = load_combined_matches(selected_competition_id, home_team, away_team)
        prediction = estimate_match_probabilities(
            standings_df,
            prediction_matches,
            home_team,
            away_team,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Gana {home_team}", f"{prediction['home_win_probability']}%")
        with col2:
            st.metric("Empate", f"{prediction['draw_probability']}%")
        with col3:
            st.metric(f"Gana {away_team}", f"{prediction['away_win_probability']}%")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.plotly_chart(probability_chart(prediction), width="stretch")

        with col2:
            goals_df = pd.DataFrame(
                [
                    {"team": home_team, "expected_goals": prediction["home_expected_goals"]},
                    {"team": away_team, "expected_goals": prediction["away_expected_goals"]},
                ]
            )
            fig = px.bar(
                goals_df,
                x="team",
                y="expected_goals",
                color="team",
                title="Goles esperados",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Goles", showlegend=True)
            st.plotly_chart(configure_plot(fig, height=360), width="stretch")

        scorelines_df = pd.DataFrame(prediction["top_scorelines"])
        scorelines_df = scorelines_df.rename(
            columns={"score": "Marcador", "probability": "Probabilidad (%)"}
        )
        st.caption("Marcadores más probables según modelo Poisson")
        render_dark_table(scorelines_df)

        form_col1, form_col2 = st.columns(2)
        with form_col1:
            st.caption(f"Forma reciente - {home_team}")
            render_dark_table(prediction["home_summary"]["recent_matches"])
        with form_col2:
            st.caption(f"Forma reciente - {away_team}")
            render_dark_table(prediction["away_summary"]["recent_matches"])

elif selected_page == "Enfrentamientos":
    col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(
            standings_df,
            x="goals_for",
            y="goals_against",
            size="points",
            color="position",
            hover_name="team",
            title="Ataque vs defensa",
            color_continuous_scale="Viridis_r",
        )
        fig.update_layout(xaxis_title="Goles a favor", yaxis_title="Goles en contra")
        st.plotly_chart(configure_plot(fig, height=460, show_colorscale=True), width="stretch")

    with col2:
        fig = px.bar(
            standings_df.sort_values("goal_difference", ascending=False),
            x="team",
            y="goal_difference",
            color="goal_difference",
            title="Diferencia de goles",
            color_continuous_scale="Teal",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Diferencia")
        st.plotly_chart(configure_plot(fig, height=460), width="stretch")
