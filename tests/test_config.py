import pytest

from app.api.football_api import FootballAPIClient
from app.database import connection


def test_schema_path_points_to_schema_file():
    assert connection.SCHEMA_PATH.name == "schema.sql"
    assert connection.SCHEMA_PATH.exists()


def test_get_connection_reports_missing_db_env_vars(monkeypatch):
    for var_name in connection.REQUIRED_DB_ENV_VARS:
        monkeypatch.delenv(var_name, raising=False)

    with pytest.raises(ValueError) as error:
        connection.get_connection()

    assert "DB_NAME" in str(error.value)
    assert "DB_PORT" in str(error.value)


def test_football_api_client_reports_missing_api_env_vars(monkeypatch):
    monkeypatch.delenv("FOOTBALL_API_URL", raising=False)
    monkeypatch.delenv("FOOTBALL_API_KEY", raising=False)

    with pytest.raises(ValueError) as error:
        FootballAPIClient()

    assert "FOOTBALL_API_URL" in str(error.value)
    assert "FOOTBALL_API_KEY" in str(error.value)


def test_football_api_client_normalizes_base_url(monkeypatch):
    monkeypatch.setenv("FOOTBALL_API_URL", "https://api.football-data.org/v4/")
    monkeypatch.setenv("FOOTBALL_API_KEY", "fake-token")

    client = FootballAPIClient()

    assert client.base_url == "https://api.football-data.org/v4"
    assert client.headers == {"X-Auth-Token": "fake-token"}
