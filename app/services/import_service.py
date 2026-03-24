from app.api.football_api import FootballAPIClient
from app.database.queries import insert_competition, insert_team

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