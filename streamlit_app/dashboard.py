import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics.match_analysis import compare_teams, estimate_match_probabilities
from app.database.read_queries import load_matches_by_team, load_standings, load_teams


st.set_page_config(
    page_title="Football Data Hub",
    page_icon="FDH",
    layout="wide",
)


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


def load_combined_matches(*team_names: str):
    frames = [load_matches_by_team(team_name) for team_name in team_names if team_name]
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
        height=360,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


standings_df = load_standings()
teams_df = load_teams()
teams_list = teams_df["name"].tolist()

st.title("Football Data Hub", anchor=False)

if standings_df.empty or not teams_list:
    st.warning("No hay datos suficientes para construir el dashboard.")
    st.stop()

display_standings_df = format_standings_table(standings_df)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Equipos", len(standings_df))
with col2:
    st.metric("Maximo de puntos", int(standings_df["points"].max()))
with col3:
    st.metric("Mejor diferencia", int(standings_df["goal_difference"].max()))
with col4:
    st.metric("Goles registrados", int(standings_df["goals_for"].sum()))

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
        st.dataframe(display_standings_df, width="stretch", hide_index=True)

    with col2:
        fig = px.bar(
            standings_df,
            x="team",
            y="points",
            color="goal_difference",
            hover_data=["played_games", "goals_for", "goals_against"],
            title="Puntos por equipo",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(height=520, xaxis_title="", yaxis_title="Puntos")
        st.plotly_chart(fig, width="stretch")

with tab2:
    selected_team = st.selectbox("Equipo", teams_list, key="matches_team")
    matches_df = load_matches_by_team(selected_team)
    display_matches_df = format_matches_table(matches_df)

    st.dataframe(display_matches_df, width="stretch", hide_index=True)

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
        fig.update_layout(height=420, xaxis_title="Fecha", yaxis_title="Goles")
        st.plotly_chart(fig, width="stretch")

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Equipo A", teams_list, key="compare_home")
    with col2:
        away_team = st.selectbox("Equipo B", teams_list, index=min(1, len(teams_list) - 1), key="compare_away")

    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes.")
    else:
        comparison_matches = load_combined_matches(home_team, away_team)
        comparison_df = compare_teams(standings_df, comparison_matches, home_team, away_team)

        fig = px.bar(
            comparison_df,
            x="metric",
            y="value",
            color="team",
            barmode="group",
            title="Comparativa de rendimiento",
        )
        fig.update_layout(height=520, xaxis_title="", yaxis_title="Valor")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(comparison_df, width="stretch", hide_index=True)

with tab4:
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Local", teams_list, key="prediction_home")
    with col2:
        away_team = st.selectbox("Visitante", teams_list, index=min(1, len(teams_list) - 1), key="prediction_away")

    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes.")
    else:
        prediction_matches = load_combined_matches(home_team, away_team)
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
            fig.update_layout(height=360, showlegend=False, xaxis_title="", yaxis_title="Goles")
            st.plotly_chart(fig, width="stretch")

        scorelines_df = pd.DataFrame(prediction["top_scorelines"])
        scorelines_df = scorelines_df.rename(
            columns={"score": "Marcador", "probability": "Probabilidad (%)"}
        )
        st.caption("Marcadores mas probables segun modelo Poisson")
        st.dataframe(scorelines_df, width="stretch", hide_index=True)

        form_col1, form_col2 = st.columns(2)
        with form_col1:
            st.caption(f"Forma reciente - {home_team}")
            st.dataframe(prediction["home_summary"]["recent_matches"], width="stretch", hide_index=True)
        with form_col2:
            st.caption(f"Forma reciente - {away_team}")
            st.dataframe(prediction["away_summary"]["recent_matches"], width="stretch", hide_index=True)

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
        fig.update_layout(height=460, xaxis_title="Goles a favor", yaxis_title="Goles en contra")
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig = px.bar(
            standings_df.sort_values("goal_difference", ascending=False),
            x="team",
            y="goal_difference",
            color="goal_difference",
            title="Diferencia de goles",
            color_continuous_scale="Teal",
        )
        fig.update_layout(height=460, xaxis_title="", yaxis_title="Diferencia")
        st.plotly_chart(fig, width="stretch")
