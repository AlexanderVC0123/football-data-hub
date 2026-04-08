from app.api.football_api import FootballAPIClient
from app.database.queries import insert_competition, insert_team, insert_season, insert_standing_row, insert_match

def import_competitions():
    """Trae competiciones desde la api y las almacena en postgres"""

    client = FootballAPIClient()
    data = client.get_competitions()

    competitions = data.get("competitions", [])

    print(f"Competiciones recibidas: {len(competitions)}")

    for competition in competitions:
        insert_competition(competition)
    
    print("Competiciones importadas correctamente")

def import_teams_by_competition(competition_code: str):
    """Trae equipos de una competición y los guarda en postgres
        Ej: PD: LaLiga"""
    
    client = FootballAPIClient()
    data = client.get_teams_by_competition(competition_code)

    teams = data.get("teams", [])

    print(f"Equipos recibidos para {competition_code}: {len(teams)}")

    for team in teams:
        insert_team(team)
    
    print(f"Equipos de la competición {competition_code} importados correctamente")

def import_current_season_by_competition(competition_code: str):
    "Obtiene la temporada actual desde standings (clasificación) y la guarda"

    client = FootballAPIClient()
    data = client.get_standing_by_competition(competition_code)

    competition = data.get("competition", {})
    season = data.get("season", {})

    if not competition or not season:
        print(f"No se puede encontrar datos de temporada para {competition_code}")
        return
    
    insert_season(season, competition.get("id"))
    print(f"Temporada actual de {competition_code} importada correctamente.")

def import_standings_by_competition(competition_code: str):
    

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

    print(f" Clasificación de {competition_code} importada correctamente")

def import_matches_by_competition(competition_code: str):
    client = FootballAPIClient()
    data = client.get_matches_by_competition(competition_code)

    matches = data.get("matches", [])

    print(f" Partidos recibidos para {competition_code}: {len(matches)}")

    for match in matches:
        insert_match(match)

    print(f" Partidos de {competition_code} importados correctamente")