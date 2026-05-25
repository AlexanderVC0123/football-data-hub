from app.database import queries
from conftest import FakeConnection
from datetime import datetime


def test_insert_sync_run_records_status(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)
    started_at = datetime(2026, 5, 7, 10, 30, 0)

    queries.insert_sync_run("PD", started_at, "SUCCESS", "OK")

    executed_query = fake_connection.cursor_instance.executed_query

    assert "INSERT INTO sync_runs" in executed_query
    assert fake_connection.cursor_instance.executed_values == (
        "PD",
        started_at,
        "SUCCESS",
        "OK",
    )
    assert fake_connection.committed is True


def test_insert_team_maps_football_api_fields(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)

    queries.insert_team(
        {
            "id": 86,
            "name": "Real Madrid CF",
            "shortName": "Real Madrid",
            "tla": "RMA",
            "founded": 1902,
            "venue": "Santiago Bernabeu",
            "website": "https://www.realmadrid.com",
            "clubColors": "White / Purple",
            "address": "Madrid",
            "crest": "https://example.com/crest.svg",
        }
    )

    executed_query = fake_connection.cursor_instance.executed_query

    assert "ON CONFLICT (api_id) DO UPDATE" in executed_query
    assert "short_name = EXCLUDED.short_name" in executed_query
    assert fake_connection.cursor_instance.executed_values == (
        86,
        "Real Madrid CF",
        "Real Madrid",
        "RMA",
        1902,
        "Santiago Bernabeu",
        "https://www.realmadrid.com",
        "White / Purple",
        "Madrid",
        "https://example.com/crest.svg",
    )
    assert fake_connection.committed is True
    assert fake_connection.closed is True


def test_insert_match_maps_group_and_last_updated(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(queries, "get_competition_db_id_by_api_id", lambda api_id, connection=None: 1)
    monkeypatch.setattr(queries, "get_season_db_id_by_api_id", lambda api_id, connection=None: 2)
    monkeypatch.setattr(
        queries,
        "get_team_db_id_by_api_id",
        lambda api_id, connection=None: {86: 3, 81: 4}[api_id],
    )

    queries.insert_match(
        {
            "id": 1001,
            "competition": {"id": 2014},
            "season": {"id": 2025},
            "matchday": 10,
            "utcDate": "2026-02-01T20:00:00Z",
            "status": "FINISHED",
            "homeTeam": {"id": 86},
            "awayTeam": {"id": 81},
            "score": {"fullTime": {"home": 2, "away": 1}},
            "winner": "HOME_TEAM",
            "stage": "REGULAR_SEASON",
            "group": "Group A",
            "lastUpdated": "2026-02-02T10:00:00Z",
        }
    )

    assert fake_connection.cursor_instance.executed_values[-2:] == (
        "Group A",
        "2026-02-02T10:00:00Z",
    )
    assert "ON CONFLICT (api_id) DO UPDATE" in fake_connection.cursor_instance.executed_query
    assert "status = EXCLUDED.status" in fake_connection.cursor_instance.executed_query
    assert "home_score = EXCLUDED.home_score" in fake_connection.cursor_instance.executed_query
    assert fake_connection.committed is True


def test_insert_standing_row_uses_valid_upsert(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(queries, "get_competition_db_id_by_api_id", lambda api_id: 1)
    monkeypatch.setattr(queries, "get_season_db_id_by_api_id", lambda api_id: 2)
    monkeypatch.setattr(queries, "get_team_db_id_by_api_id", lambda api_id: 3)

    queries.insert_standing_row(
        {
            "position": 1,
            "team": {"id": 86, "name": "Real Madrid CF"},
            "playedGames": 20,
            "won": 15,
            "draw": 3,
            "lost": 2,
            "points": 48,
            "goalsFor": 45,
            "goalsAgainst": 18,
            "goalDifference": 27,
            "form": "W,W,D,L,W",
        },
        competition_api_id=2014,
        season_api_id=2025,
    )

    executed_query = fake_connection.cursor_instance.executed_query

    assert "ON CONFLICT (season_id, team_id) DO UPDATE" in executed_query
    assert "SET" in executed_query
    assert "points = EXCLUDED.points" in executed_query
    assert "updated_at = CURRENT_TIMESTAMP" in executed_query
    assert fake_connection.cursor_instance.executed_values == (
        1,
        2,
        3,
        1,
        20,
        15,
        3,
        2,
        48,
        45,
        18,
        27,
        "W,W,D,L,W",
    )


def test_insert_competition_team_creates_relation(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(queries, "get_competition_db_id_by_api_id", lambda api_id: 1)
    monkeypatch.setattr(queries, "get_team_db_id_by_api_id", lambda api_id: 2)
    monkeypatch.setattr(queries, "get_season_db_id_by_api_id", lambda api_id: 3)

    queries.insert_competition_team(
        team_api_id=86,
        competition_api_id=2014,
        season_api_id=2025,
    )

    executed_query = fake_connection.cursor_instance.executed_query

    assert "INSERT INTO competition_teams" in executed_query
    assert "ON CONFLICT (competition_id, team_id, season_id) DO UPDATE" in executed_query
    assert fake_connection.cursor_instance.executed_values == (1, 2, 3)
    assert fake_connection.committed is True


def test_insert_match_does_not_insert_when_related_ids_are_missing(monkeypatch):
    fake_connection = FakeConnection()
    monkeypatch.setattr(queries, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(queries, "get_competition_db_id_by_api_id", lambda api_id, connection=None: None)
    monkeypatch.setattr(queries, "get_season_db_id_by_api_id", lambda api_id, connection=None: 2)
    monkeypatch.setattr(queries, "get_team_db_id_by_api_id", lambda api_id,connection=None: 3)

    queries.insert_match({"id": 1001})

    assert fake_connection.cursor_instance.executed_query is None
    assert fake_connection.committed is False
