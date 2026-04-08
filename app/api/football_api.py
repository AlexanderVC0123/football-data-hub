import os
import requests
from dotenv import load_dotenv

load_dotenv()

class FootballAPIClient:
    "Cliente sencillo para consumir api en football-data.org"

    def __init__(self):
        self.base_url = os.getenv("FOOTBALL_API_URL")
        self.api_key = os.getenv("FOOTBALL_API_KEY")

        self.headers = {
            "X-Auth-Token": self.api_key
        }
    
    def get_competitions(self):
        "Obtiene la lista de competiciones."

        url = f"{self.base_url}/competitions"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_teams_by_competition(self, competition_code: str):
        """Obtiene los equipos de una competición usando su código.
            Ejemplo: PD = LaLiga"""
        
        url = f"{self.base_url}/competitions/{competition_code}/teams"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_standing_by_competition(self, competition_code:str):
        """Obtiene la clasificación actual de una competición"""

        url = f"{self.base_url}/competitions/{competition_code}/standings"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_matches_by_competition(self, competition_code:str):
        """Obtiene los partidos de una temporada activa de la competición"""

        url = f"{self.base_url}/competitions/{competition_code}/matches"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()