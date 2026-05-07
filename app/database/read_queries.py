import pandas as pd

from app.database.connection import get_connection


def load_competitions():
    """Carga las competiciones disponibles en la base de datos."""

    query = """
        SELECT id, api_id, name, code, country_name, type
        FROM competitions
        ORDER BY name;
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def load_last_sync_run(competition_code: str):
    """Carga el ultimo intento de sincronizacion de una competicion."""

    query = """
        SELECT competition_code, started_at, finished_at, status, message
        FROM sync_runs
        WHERE competition_code = %s
        ORDER BY finished_at DESC
        LIMIT 1;
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=(competition_code,))
    finally:
        conn.close()


def load_standings(competition_id: int | None = None):
    """Carga la clasificacion, opcionalmente filtrada por competicion."""

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
    """
    params = None

    if competition_id is not None:
        query += " WHERE s.competition_id = %s"
        params = (competition_id,)

    query += " ORDER BY s.position;"

    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


def load_teams(competition_id: int | None = None):
    """Carga equipos usando la relacion explicita competicion-equipo."""

    if competition_id is None:
        query = """
            SELECT name
            FROM teams
            ORDER BY name;
        """
        params = None
    else:
        query = """
            WITH related_teams AS (
                SELECT team_id
                FROM competition_teams
                WHERE competition_id = %s

                UNION

                SELECT team_id
                FROM standings
                WHERE competition_id = %s

                UNION

                SELECT home_team_id AS team_id
                FROM matches
                WHERE competition_id = %s

                UNION

                SELECT away_team_id AS team_id
                FROM matches
                WHERE competition_id = %s
            )
            SELECT DISTINCT t.name
            FROM related_teams rt
            JOIN teams t ON t.id = rt.team_id
            ORDER BY t.name;
        """
        params = (competition_id, competition_id, competition_id, competition_id)

    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


def load_matches_by_team(team_name: str, competition_id: int | None = None):
    """Carga los partidos de un equipo concreto, con filtro opcional de competicion."""

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
        WHERE (ht.name = %s OR at.name = %s)
    """
    params = [team_name, team_name]

    if competition_id is not None:
        query += " AND m.competition_id = %s"
        params.append(competition_id)

    query += " ORDER BY m.utc_date;"

    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=tuple(params))
    finally:
        conn.close()
