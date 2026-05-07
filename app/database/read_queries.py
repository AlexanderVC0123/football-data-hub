import pandas as pd

from app.database.connection import get_connection


def load_standings():
    """Carga la clasificacion actual."""

    query = """
        SELECT
            s.position,
            t.name AS team,
            s.played_games,
            s.won,
            s.draw,
            s.lost,
            s.points,
            s.goals_for,
            s.goals_against,
            s.goal_difference
        FROM standings s
        JOIN teams t ON s.team_id = t.id
        ORDER BY s.position;
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def load_teams():
    """Carga el listado de equipos."""

    query = """
        SELECT name
        FROM teams
        ORDER BY name;
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def load_matches_by_team(team_name: str):
    """Carga los partidos de un equipo concreto."""

    query = """
        SELECT
            m.matchday,
            m.utc_date,
            ht.name AS home_team,
            at.name AS away_team,
            m.home_score,
            m.away_score,
            m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE ht.name = %s
        OR at.name = %s
        ORDER BY m.utc_date;
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=(team_name, team_name))
    finally:
        conn.close()
