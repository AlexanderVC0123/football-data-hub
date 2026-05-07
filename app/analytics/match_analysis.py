from __future__ import annotations

import math

import pandas as pd


def _safe_float(value, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    return float(value)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _poisson_probability(expected_goals: float, goals: int) -> float:
    """Calcula la probabilidad de marcar X goles con una media esperada."""

    expected_goals = max(expected_goals, 0.01)
    return (math.exp(-expected_goals) * expected_goals**goals) / math.factorial(goals)


def _finished_matches(matches_df: pd.DataFrame) -> pd.DataFrame:
    if matches_df.empty:
        return matches_df.copy()

    df = matches_df.copy()
    df = df[df["status"].eq("FINISHED")]
    df = df[df["home_score"].notna() & df["away_score"].notna()]

    if "utc_date" in df.columns:
        df["utc_date"] = pd.to_datetime(df["utc_date"], errors="coerce")
        df = df.sort_values("utc_date", ascending=False)

    return df


def get_team_recent_form(matches_df: pd.DataFrame, team_name: str, limit: int = 5) -> pd.DataFrame:
    """Devuelve los ultimos partidos finalizados de un equipo con resultado calculado."""

    df = _finished_matches(matches_df)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "utc_date",
                "opponent",
                "venue",
                "goals_for",
                "goals_against",
                "result",
                "points",
            ]
        )

    team_matches = df[(df["home_team"].eq(team_name)) | (df["away_team"].eq(team_name))].head(limit)
    rows = []

    for _, match in team_matches.iterrows():
        is_home = match["home_team"] == team_name
        goals_for = match["home_score"] if is_home else match["away_score"]
        goals_against = match["away_score"] if is_home else match["home_score"]

        if goals_for > goals_against:
            result = "W"
            points = 3
        elif goals_for == goals_against:
            result = "D"
            points = 1
        else:
            result = "L"
            points = 0

        rows.append(
            {
                "utc_date": match.get("utc_date"),
                "opponent": match["away_team"] if is_home else match["home_team"],
                "venue": "Local" if is_home else "Visitante",
                "goals_for": int(goals_for),
                "goals_against": int(goals_against),
                "result": result,
                "points": points,
            }
        )

    return pd.DataFrame(rows)


def summarize_team(
    standings_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    team_name: str,
    recent_limit: int = 5,
) -> dict:
    """Resume posicion, rendimiento global y forma reciente de un equipo."""

    standing_rows = standings_df[standings_df["team"].eq(team_name)]
    if standing_rows.empty:
        raise ValueError(f"No hay datos de clasificacion para el equipo: {team_name}")

    row = standing_rows.iloc[0]
    played_games = max(_safe_float(row["played_games"], 0.0), 1.0)
    recent_form = get_team_recent_form(matches_df, team_name, recent_limit)

    recent_points_per_game = (
        _safe_float(recent_form["points"].mean(), 0.0) if not recent_form.empty else 0.0
    )
    recent_goals_for = (
        _safe_float(recent_form["goals_for"].mean(), 0.0) if not recent_form.empty else 0.0
    )
    recent_goals_against = (
        _safe_float(recent_form["goals_against"].mean(), 0.0) if not recent_form.empty else 0.0
    )

    return {
        "team": team_name,
        "position": int(row["position"]),
        "played_games": int(row["played_games"]),
        "points": int(row["points"]),
        "points_per_game": _safe_float(row["points"]) / played_games,
        "goals_for_per_game": _safe_float(row["goals_for"]) / played_games,
        "goals_against_per_game": _safe_float(row["goals_against"]) / played_games,
        "goal_difference_per_game": _safe_float(row["goal_difference"]) / played_games,
        "recent_points_per_game": recent_points_per_game,
        "recent_goals_for": recent_goals_for,
        "recent_goals_against": recent_goals_against,
        "recent_form": "".join(recent_form["result"].tolist()),
        "recent_matches": recent_form,
    }


def compare_teams(
    standings_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    home_team: str,
    away_team: str,
) -> pd.DataFrame:
    """Crea una tabla larga con metricas comparables entre dos equipos."""

    home = summarize_team(standings_df, matches_df, home_team)
    away = summarize_team(standings_df, matches_df, away_team)

    metrics = [
        ("Puntos por partido", "points_per_game"),
        ("Goles a favor por partido", "goals_for_per_game"),
        ("Goles en contra por partido", "goals_against_per_game"),
        ("Diferencia de goles por partido", "goal_difference_per_game"),
        ("Forma reciente PPG", "recent_points_per_game"),
        ("Goles recientes a favor", "recent_goals_for"),
        ("Goles recientes en contra", "recent_goals_against"),
    ]

    rows = []
    for label, key in metrics:
        rows.append({"metric": label, "team": home_team, "value": round(home[key], 2)})
        rows.append({"metric": label, "team": away_team, "value": round(away[key], 2)})

    return pd.DataFrame(rows)


def _league_goals_per_team_match(standings_df: pd.DataFrame) -> float:
    total_played_games = max(_safe_float(standings_df["played_games"].sum()), 1.0)
    total_goals = _safe_float(standings_df["goals_for"].sum())
    return max(total_goals / total_played_games, 0.8)


def _estimate_expected_goals(home: dict, away: dict, standings_df: pd.DataFrame) -> tuple[float, float]:
    league_avg = _league_goals_per_team_match(standings_df)

    # Mezclamos rendimiento de temporada, forma reciente y media de liga para evitar
    # que una muestra pequena de partidos recientes domine toda la prediccion.
    home_attack = (
        0.55 * home["goals_for_per_game"]
        + 0.25 * home["recent_goals_for"]
        + 0.20 * league_avg
    )
    away_attack = (
        0.55 * away["goals_for_per_game"]
        + 0.25 * away["recent_goals_for"]
        + 0.20 * league_avg
    )
    home_defense_allowed = (
        0.60 * home["goals_against_per_game"]
        + 0.25 * home["recent_goals_against"]
        + 0.15 * league_avg
    )
    away_defense_allowed = (
        0.60 * away["goals_against_per_game"]
        + 0.25 * away["recent_goals_against"]
        + 0.15 * league_avg
    )

    # La media de goles esperados cruza ataque propio con fragilidad defensiva rival.
    # El local recibe un pequeno bonus porque historicamente jugar en casa importa.
    home_expected_goals = (0.58 * home_attack + 0.42 * away_defense_allowed) * 1.08
    away_expected_goals = (0.58 * away_attack + 0.42 * home_defense_allowed) * 0.96

    return (
        round(_clamp(home_expected_goals, 0.2, 4.5), 2),
        round(_clamp(away_expected_goals, 0.2, 4.5), 2),
    )


def _build_score_matrix(
    home_expected_goals: float,
    away_expected_goals: float,
    max_goals: int = 6,
) -> pd.DataFrame:
    rows = []

    # Cada celda de la matriz representa P(local marca i) * P(visitante marca j).
    # Esto asume independencia entre goles de ambos equipos, que es la base del
    # modelo Poisson simple usado en muchas primeras aproximaciones deportivas.
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = _poisson_probability(home_expected_goals, home_goals) * _poisson_probability(
                away_expected_goals,
                away_goals,
            )
            rows.append(
                {
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "score": f"{home_goals}-{away_goals}",
                    "probability": probability,
                }
            )

    score_matrix = pd.DataFrame(rows)
    probability_sum = score_matrix["probability"].sum()
    if probability_sum > 0:
        score_matrix["probability"] = score_matrix["probability"] / probability_sum

    return score_matrix


def _top_scorelines(score_matrix: pd.DataFrame, limit: int = 5) -> list[dict]:
    top_scores = score_matrix.sort_values("probability", ascending=False).head(limit)
    return [
        {
            "score": row["score"],
            "probability": round(row["probability"] * 100, 1),
        }
        for _, row in top_scores.iterrows()
    ]


def estimate_match_probabilities(
    standings_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    home_team: str,
    away_team: str,
) -> dict:
    """Estima probabilidades usando un modelo Poisson simple."""

    home = summarize_team(standings_df, matches_df, home_team)
    away = summarize_team(standings_df, matches_df, away_team)

    home_expected_goals, away_expected_goals = _estimate_expected_goals(
        home,
        away,
        standings_df,
    )
    score_matrix = _build_score_matrix(home_expected_goals, away_expected_goals)

    # Las probabilidades finales salen de sumar todos los marcadores posibles:
    # local gana si goles_local > goles_visitante, empate si son iguales, etc.
    home_probability = score_matrix.loc[
        score_matrix["home_goals"] > score_matrix["away_goals"],
        "probability",
    ].sum()
    draw_probability = score_matrix.loc[
        score_matrix["home_goals"] == score_matrix["away_goals"],
        "probability",
    ].sum()
    away_probability = score_matrix.loc[
        score_matrix["home_goals"] < score_matrix["away_goals"],
        "probability",
    ].sum()

    return {
        "home_team": home_team,
        "away_team": away_team,
        "model": "poisson",
        "home_win_probability": round(home_probability * 100, 1),
        "draw_probability": round(draw_probability * 100, 1),
        "away_win_probability": round(away_probability * 100, 1),
        "home_expected_goals": home_expected_goals,
        "away_expected_goals": away_expected_goals,
        "total_expected_goals": round(home_expected_goals + away_expected_goals, 2),
        "top_scorelines": _top_scorelines(score_matrix),
        "score_matrix": score_matrix,
        "home_summary": home,
        "away_summary": away,
    }
