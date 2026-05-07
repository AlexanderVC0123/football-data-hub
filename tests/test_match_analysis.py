import pandas as pd

from app.analytics.match_analysis import (
    compare_teams,
    estimate_match_probabilities,
    get_team_recent_form,
    summarize_team,
)


def sample_standings():
    return pd.DataFrame(
        [
            {
                "position": 1,
                "team": "Barcelona",
                "played_games": 10,
                "won": 8,
                "draw": 1,
                "lost": 1,
                "points": 25,
                "goals_for": 26,
                "goals_against": 9,
                "goal_difference": 17,
            },
            {
                "position": 2,
                "team": "Real Madrid",
                "played_games": 10,
                "won": 7,
                "draw": 2,
                "lost": 1,
                "points": 23,
                "goals_for": 22,
                "goals_against": 10,
                "goal_difference": 12,
            },
        ]
    )


def sample_matches():
    return pd.DataFrame(
        [
            {
                "matchday": 10,
                "utc_date": "2026-04-10T20:00:00Z",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "home_score": 2,
                "away_score": 1,
                "status": "FINISHED",
            },
            {
                "matchday": 9,
                "utc_date": "2026-04-03T20:00:00Z",
                "home_team": "Valencia",
                "away_team": "Barcelona",
                "home_score": 1,
                "away_score": 1,
                "status": "FINISHED",
            },
            {
                "matchday": 9,
                "utc_date": "2026-04-02T20:00:00Z",
                "home_team": "Real Madrid",
                "away_team": "Sevilla",
                "home_score": 3,
                "away_score": 0,
                "status": "FINISHED",
            },
            {
                "matchday": 11,
                "utc_date": "2026-04-17T20:00:00Z",
                "home_team": "Barcelona",
                "away_team": "Athletic Club",
                "home_score": None,
                "away_score": None,
                "status": "TIMED",
            },
        ]
    )


def test_get_team_recent_form_calculates_results():
    form = get_team_recent_form(sample_matches(), "Barcelona", limit=3)

    assert form["result"].tolist() == ["W", "D"]
    assert form["points"].tolist() == [3, 1]
    assert form.iloc[0]["opponent"] == "Real Madrid"


def test_summarize_team_combines_table_and_recent_form():
    summary = summarize_team(sample_standings(), sample_matches(), "Barcelona")

    assert summary["team"] == "Barcelona"
    assert summary["points_per_game"] == 2.5
    assert summary["recent_form"] == "WD"


def test_compare_teams_returns_long_metric_table():
    comparison = compare_teams(
        sample_standings(),
        sample_matches(),
        "Barcelona",
        "Real Madrid",
    )

    assert set(comparison["team"]) == {"Barcelona", "Real Madrid"}
    assert "Puntos por partido" in comparison["metric"].tolist()


def test_estimate_match_probabilities_returns_balanced_probabilities():
    prediction = estimate_match_probabilities(
        sample_standings(),
        sample_matches(),
        "Barcelona",
        "Real Madrid",
    )

    total_probability = (
        prediction["home_win_probability"]
        + prediction["draw_probability"]
        + prediction["away_win_probability"]
    )

    assert round(total_probability) == 100
    assert prediction["model"] == "poisson"
    assert prediction["home_expected_goals"] > 0
    assert prediction["away_expected_goals"] > 0
    assert len(prediction["top_scorelines"]) == 5
    assert prediction["score_matrix"]["probability"].sum().round(6) == 1
