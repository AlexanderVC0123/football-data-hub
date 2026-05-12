import pandas as pd

from app.analytics.dashboard_metrics import calculate_competition_kpis


def test_calculate_competition_kpis_returns_useful_sports_insights():
    standings_df = pd.DataFrame(
        [
            {
                "position": 1,
                "team": "Barcelona",
                "points": 80,
                "goals_for": 75,
                "goals_against": 30,
            },
            {
                "position": 2,
                "team": "Real Madrid",
                "points": 78,
                "goals_for": 82,
                "goals_against": 35,
            },
            {
                "position": 3,
                "team": "Atletico",
                "points": 70,
                "goals_for": 62,
                "goals_against": 25,
            },
        ]
    )
    matches_df = pd.DataFrame(
        [
            {
                "utc_date": "2026-05-01T20:00:00Z",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "home_score": 3,
                "away_score": 2,
                "status": "FINISHED",
            },
            {
                "utc_date": "2026-05-03T20:00:00Z",
                "home_team": "Atletico",
                "away_team": "Barcelona",
                "home_score": 1,
                "away_score": 1,
                "status": "FINISHED",
            },
            {
                "utc_date": "2026-05-10T20:00:00Z",
                "home_team": "Real Madrid",
                "away_team": "Atletico",
                "home_score": None,
                "away_score": None,
                "status": "TIMED",
            },
        ]
    )

    kpis = calculate_competition_kpis(standings_df, matches_df)

    assert kpis["leader"]["value"] == "Barcelona"
    assert kpis["top_attack"]["value"] == "Real Madrid"
    assert kpis["best_defense"]["value"] == "Atletico"
    assert kpis["goals_per_match"]["value"] == "3.50"
    assert kpis["highest_scoring_match"]["value"] == "Barcelona 3-2 Real Madrid"
    assert kpis["next_match"]["value"] == "Real Madrid vs Atletico"
    assert kpis["completion_rate"]["value"] == "2/3"
    assert kpis["pending_matches"]["value"] == "1"
