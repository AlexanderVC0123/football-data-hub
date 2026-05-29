from datetime import datetime

from app.api.football_api import FootballAPIClient
from app.config import DEFAULT_COMPETITIONS
from app.database.connection import execute_schema
from app.database.queries import (
    insert_competition,
    insert_competition_team,
    insert_match,
    insert_season,
    insert_standing_row,
    insert_sync_run,
    insert_team,
)
from app.database.connection import get_connection


def sync_competition_data(competition_code: str):
    """Sincroniza una competicion completa desde la API."""

    competition_code = competition_code.upper()

    execute_schema()

    started_at = datetime.now()
    connection = get_connection()

    try:
        import_competitions(connection)
        import_teams_by_competition(competition_code, connection)
        import_current_season_by_competition(competition_code, connection)
        import_standings_by_competition(competition_code, connection)
        import_matches_by_competition(competition_code, connection)

        insert_sync_run(competition_code, started_at, "SUCCESS", "Sincronización completada", connection)
        print(f"Sincronización de {competition_code} completada")

        connection.commit()
    except Exception as error:
        # Guardamos también los fallos para que web y desktop puedan mostrar
        # cuando fue el último intento y por que no actualizó correctamente.
        insert_sync_run(competition_code, started_at, "FAILED", str(error))
        connection.rollback()
        raise
    finally:
        connection.close()

def sync_competitions(competition_codes: list[str] | None = None):
    """Sincroniza varias competiciones de forma secuencial."""

    codes = competition_codes or DEFAULT_COMPETITIONS

    for competition_code in codes:
        sync_competition_data(competition_code)


def import_competitions(connection=None):
    """Trae competiciones desde la API y las sincroniza en PostgreSQL."""

    client = FootballAPIClient()
    data = client.get_competitions()
    competitions = data.get("competitions", [])

    print(f"Competiciones recibidas: {len(competitions)}")

    for competition in competitions:
        insert_competition(competition)

    print("Competiciones importadas correctamente")


def import_teams_by_competition(competition_code: str, connection=None):
    """Trae equipos de una competición y guarda la relación competición-equipo."""

    client = FootballAPIClient()
    data = client.get_teams_by_competition(competition_code)

    competition = data.get("competition", {})
    season = data.get("season", {})
    teams = data.get("teams", [])

    print(f"Equipos recibidos para {competition_code}: {len(teams)}")

    if competition:
        insert_competition(competition)

    if competition and season:
        # La relación competition_teams necesita que la temporada exista antes.
        insert_season(season, competition.get("id"))

    for team in teams:
        insert_team(team)
        if competition and season:
            insert_competition_team(
                team.get("id"),
                competition.get("id"),
                season.get("id"),
            )

    print(f"Equipos de la competición {competition_code} importados correctamente")


def import_current_season_by_competition(competition_code: str, connection=None):
    """Obtiene la temporada actual desde standings y la sincroniza."""

    client = FootballAPIClient()
    data = client.get_standing_by_competition(competition_code)

    competition = data.get("competition", {})
    season = data.get("season", {})

    if not competition or not season:
        print(f"No se encontraron datos de temporada para {competition_code}")
        return

    insert_competition(competition)
    insert_season(season, competition.get("id"))
    print(f"Temporada actual de {competition_code} importada correctamente")


def import_standings_by_competition(competition_code: str, connection=None):
    """Trae la clasificación total de una competicion y la sincroniza."""

    client = FootballAPIClient()
    data = client.get_standing_by_competition(competition_code)

    competition = data.get("competition", {})
    season = data.get("season", {})
    standings = data.get("standings", [])

    if not standings:
        print(f"No se encontraron standings para {competition_code}")
        return

    total_table = None
    for standing_block in standings:
        if standing_block.get("type") == "TOTAL":
            total_table = standing_block.get("table", [])
            break

    if total_table is None:
        print(f"No se encontro la tabla total para {competition_code}")
        return

    for row in total_table:
        insert_standing_row(row, competition.get("id"), season.get("id"))
        insert_competition_team(
            row.get("team", {}).get("id"),
            competition.get("id"),
            season.get("id"),
        )

    print(f"Clasificación de {competition_code} importada correctamente")


def import_matches_by_competition(competition_code: str, connection=None):
    """Trae los partidos de una competicion y los sincroniza."""

    client = FootballAPIClient()
    data = client.get_matches_by_competition(competition_code)
    matches = data.get("matches", [])

    print(f"Partidos recibidos para {competition_code}: {len(matches)}")

    for match in matches:
        insert_match(match, connection)

    print(f"Partidos de {competition_code} importados correctamente")
