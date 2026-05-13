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
from auth_page import inicializar_sesion, mostrar_login, mostrar_sidebar_sesion


st.set_page_config(
    page_title="Football Data Hub",
    page_icon="./assets/icons/fdh_icon.ico",
    layout="wide",
)

inicializar_sesion()

if not st.session_state.logueado:
    mostrar_login()
    st.stop()

mostrar_sidebar_sesion()

# Asegura tablas nuevas como sync_runs antes de leer datos para construir la UI.
execute_schema()


def apply_page_styles():
    st.markdown(
        """
        <style>
        .fdh-empty {
            border: 1px solid #243044;
            background: #111827;
            padding: 28px;
            border-radius: 8px;
            color: #d1d5db;
        }
        .fdh-empty h3 {
            color: #f9fafb;
            margin: 0 0 8px 0;
        }
        .fdh-header {
            border: 1px solid #243044;
            background: #0f172a;
            padding: 24px 28px;
            border-radius: 8px;
            margin-bottom: 18px;
        }
        .fdh-header-content {
            display: flex;
            align-items: center;
            gap: 18px;
        }
        .fdh-logo {
            width: 100px;
            height: 100px;
            object-fit: contain;
            flex: 0 0 auto;
        }
        .fdh-header h1 {
            margin: 0;
            color: #f9fafb;
            font-size: 2rem;
            line-height: 1.15;
        }
        .fdh-header p {
            margin: 8px 0 0 0;
            color: #9ca3af;
            max-width: 900px;
        }
        @media (max-width: 640px) {
            .fdh-header {
                padding: 20px;
            }
            .fdh-header-content {
                gap: 14px;
            }
            .fdh-logo {
                width: 46px;
                height: 46px;
            }
            .fdh-header h1 {
                font-size: 1.55rem;
            }
        }
        .fdh-status {
            border: 1px solid #243044;
            background: #111827;
            color: #d1d5db;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 8px 0 16px 0;
            font-size: 0.92rem;
        }
        .fdh-table {
            width: 100%;
            border-collapse: collapse;
            background: #111827;
            color: #e5e7eb;
            border: 1px solid #243044;
            border-radius: 8px;
            overflow: hidden;
            font-size: 0.9rem;
        }
        .fdh-table th {
            background: #172033;
            color: #9ca3af;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #243044;
        }
        .fdh-table td {
            padding: 9px 12px;
            border-bottom: 1px solid #1f2937;
        }
        .fdh-table tr:last-child td {
            border-bottom: 0;
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

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def render_header():

    BASE_DIR = Path(__file__).resolve().parent.parent
    logo_path = BASE_DIR / "assets" / "branding" / "fdh_logo_web_512.webp"
    logo_base64 = image_to_base64(logo_path)

    st.markdown(
        f"""
        <div class="fdh-header">
            <div class="fdh-header-content">
                <img src="data:image/webp;base64,{logo_base64}" class="fdh-logo" alt="Football Data Hub">
                <div>
                    <h1>Football Data Hub</h1>
                    <p>Panel de análisis futbolístico para explorar competiciones, clasificaciones, partidos y predicciones basadas en datos sincronizados.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sync_status(last_sync_df: pd.DataFrame):
    if last_sync_df.empty:
        text = "Última actualización: sin sincronizaciones registradas."
    else:
        last_sync = last_sync_df.iloc[0]
        status_label = "correcta" if last_sync["status"] == "SUCCESS" else "fallida"
        message = last_sync.get("message") or ""
        text = f"Ultima actualizacion: {last_sync['finished_at']} | Estado: {status_label} | {message}"

    st.markdown(f'<div class="fdh-status">{text}</div>', unsafe_allow_html=True)


def render_dark_table(df: pd.DataFrame, max_rows: int | None = None):
    display_df = df.head(max_rows) if max_rows else df
    html = display_df.to_html(index=False, classes="fdh-table", border=0, escape=True)
    st.markdown(html, unsafe_allow_html=True)


def configure_plot(fig, height: int = 420):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#111827",
        font_color="#e5e7eb",
        height=height,
        margin=dict(l=20, r=20, t=50, b=30),
    )
    return fig


apply_page_styles()


def format_standings_table(df: pd.DataFrame):
    return df.rename(
        columns={
            "position": "Posicion",
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


render_header()

competitions_df = load_competitions()
if competitions_df.empty:
    render_empty_state(
        "Datos en preparacion",
        "Todavia no hay competiciones cargadas. Cuando el proceso de sincronizacion termine, este panel mostrara las ligas disponibles automaticamente.",
    )
    st.stop()

competition_options = {
    f"{row['name']} ({row['code']})": {"id": int(row["id"]), "code": row["code"]}
    for _, row in competitions_df.iterrows()
}
selected_competition_label = st.selectbox("Competicion", list(competition_options.keys()))
selected_competition = competition_options[selected_competition_label]
selected_competition_id = selected_competition["id"]
selected_competition_code = selected_competition["code"]

last_sync_df = load_last_sync_run(selected_competition_code)
render_sync_status(last_sync_df)

if manual_sync_enabled() and st.button("Actualizar competicion desde API"):
    # La sincronizacion usa upserts: si el registro ya existe, se actualiza con
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
        "Competicion sin datos analiticos",
        "La competicion existe en la base, pero aun no tiene clasificacion o equipos asociados. El panel se completara despues de la proxima sincronizacion.",
    )
    st.stop()

display_standings_df = format_standings_table(standings_df)
kpis = calculate_competition_kpis(standings_df, competition_matches_df)

main_kpi_cols = st.columns(4)
for column, key in zip(
    main_kpi_cols,
    ["leader", "top_attack", "best_defense", "goals_per_match"],
):
    item = kpis[key]
    with column:
        st.metric(item["label"], item["value"], item["detail"])

secondary_kpi_cols = st.columns(4)
for column, key in zip(
    secondary_kpi_cols,
    ["highest_scoring_match", "next_match", "completion_rate", "pending_matches"],
):
    item = kpis[key]
    with column:
        st.metric(item["label"], item["value"], item["detail"])

overview_col1, overview_col2, overview_col3 = st.columns(3)
with overview_col1:
    attack_fig = px.bar(
        standings_df.sort_values("goals_for", ascending=False).head(6),
        x="team",
        y="goals_for",
        color="goals_for",
        title="Ataques mas productivos",
        color_continuous_scale="Greens",
    )
    attack_fig.update_layout(xaxis_title="", yaxis_title="Goles")
    st.plotly_chart(configure_plot(attack_fig, height=340), width="stretch")

with overview_col2:
    defense_fig = px.bar(
        standings_df.sort_values("goals_against", ascending=True).head(6),
        x="team",
        y="goals_against",
        color="goals_against",
        title="Defensas mas solidas",
        color_continuous_scale="Blues_r",
    )
    defense_fig.update_layout(xaxis_title="", yaxis_title="Goles encajados")
    st.plotly_chart(configure_plot(defense_fig, height=340), width="stretch")

with overview_col3:
    efficiency_df = standings_df.copy()
    efficiency_df["points_per_game"] = efficiency_df["points"] / efficiency_df["played_games"].replace(0, 1)
    efficiency_df["goal_difference_size"] = efficiency_df["goal_difference"].abs() + 1
    efficiency_fig = px.scatter(
        efficiency_df,
        x="goals_for",
        y="points_per_game",
        size="goal_difference_size",
        color="position",
        hover_name="team",
        hover_data=["goal_difference"],
        title="Eficiencia ofensiva",
        color_continuous_scale="Viridis_r",
    )
    efficiency_fig.update_layout(xaxis_title="Goles a favor", yaxis_title="Puntos/partido")
    st.plotly_chart(configure_plot(efficiency_fig, height=340), width="stretch")

st.divider()
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Clasificacion",
        "Partidos",
        "Comparador",
        "Prediccion",
        "Estadisticas",
    ]
)

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        render_dark_table(display_standings_df)

    with col2:
        fig = px.bar(
            standings_df,
            x="team",
            y="points",
            color="goal_difference",
            hover_data=["played_games", "goals_for", "goals_against"],
            title="Puntos por equipo",
            color_continuous_scale="Blues",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Puntos")
        st.plotly_chart(configure_plot(fig, height=520), width="stretch")

with tab2:
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

with tab3:
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
        fig.update_layout(xaxis_title="", yaxis_title="Valor")
        st.plotly_chart(configure_plot(fig, height=520), width="stretch")
        render_dark_table(comparison_df)

with tab4:
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
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Goles")
            st.plotly_chart(configure_plot(fig, height=360), width="stretch")

        scorelines_df = pd.DataFrame(prediction["top_scorelines"])
        scorelines_df = scorelines_df.rename(
            columns={"score": "Marcador", "probability": "Probabilidad (%)"}
        )
        st.caption("Marcadores mas probables segun modelo Poisson")
        render_dark_table(scorelines_df)

        form_col1, form_col2 = st.columns(2)
        with form_col1:
            st.caption(f"Forma reciente - {home_team}")
            render_dark_table(prediction["home_summary"]["recent_matches"])
        with form_col2:
            st.caption(f"Forma reciente - {away_team}")
            render_dark_table(prediction["away_summary"]["recent_matches"])

with tab5:
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
        st.plotly_chart(configure_plot(fig, height=460), width="stretch")

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
