import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

REQUIRED_API_ENV_VARS = ("FOOTBALL_API_URL", "FOOTBALL_API_KEY")


def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Falta la variable de entorno requerida: {var_name}")
    return value


class FootballAPIClient:
    """Cliente sencillo para consumir la API de football-data.org."""

    def __init__(self):
        missing_vars = [var_name for var_name in REQUIRED_API_ENV_VARS if not os.getenv(var_name)]
        if missing_vars:
            raise ValueError(
                "Faltan variables de entorno requeridas para la API: "
                + ", ".join(missing_vars)
            )

        self.base_url = get_required_env("FOOTBALL_API_URL").rstrip("/")
        self.api_key = get_required_env("FOOTBALL_API_KEY")
        self.headers = {"X-Auth-Token": self.api_key}

    def get_competitions(self):
        """Obtiene la lista de competiciones."""

        url = f"{self.base_url}/competitions"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_teams_by_competition(self, competition_code: str):
        """Obtiene los equipos de una competicion usando su codigo."""

        url = f"{self.base_url}/competitions/{competition_code}/teams"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_standing_by_competition(self, competition_code: str):
        """Obtiene la clasificación actual de una competicion."""

        url = f"{self.base_url}/competitions/{competition_code}/standings"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_matches_by_competition(self, competition_code: str):
        """Obtiene los partidos de una temporada activa de la competicion."""

        url = f"{self.base_url}/competitions/{competition_code}/matches"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
