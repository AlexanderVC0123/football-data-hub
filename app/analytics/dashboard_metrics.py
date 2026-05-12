from __future__ import annotations

import pandas as pd


def _format_match(row: pd.Series) -> str:
    return f"{row['home_team']} vs {row['away_team']}"


def calculate_competition_kpis(standings_df: pd.DataFrame, matches_df: pd.DataFrame) -> dict:
    """Calcula indicadores principales para resumir una competicion."""

    leader = standings_df.sort_values("position").iloc[0]
    top_attack = standings_df.sort_values("goals_for", ascending=False).iloc[0]
    best_defense = standings_df.sort_values("goals_against", ascending=True).iloc[0]

    # Solo usamos partidos finalizados para medias de goles, porque los pendientes
    # no tienen marcador definitivo y distorsionarian el analisis.
    finished_matches = matches_df[matches_df["status"].eq("FINISHED")].copy()
    finished_matches = finished_matches[
        finished_matches["home_score"].notna() & finished_matches["away_score"].notna()
    ]
    pending_matches = matches_df[~matches_df["status"].eq("FINISHED")].copy()

    if finished_matches.empty:
        goals_per_match = 0.0
        highest_scoring_match = "Sin partidos finalizados"
        highest_scoring_detail = "0 goles"
    else:
        finished_matches["total_goals"] = (
            finished_matches["home_score"].fillna(0) + finished_matches["away_score"].fillna(0)
        )
        goals_per_match = float(finished_matches["total_goals"].mean())
        highest = finished_matches.sort_values("total_goals", ascending=False).iloc[0]
        highest_scoring_match = (
            f"{highest['home_team']} {int(highest['home_score'])}-"
            f"{int(highest['away_score'])} {highest['away_team']}"
        )
        highest_scoring_detail = f"{int(highest['total_goals'])} goles"

    next_match = "Sin partidos pendientes"
    next_match_detail = ""
    if not pending_matches.empty:
        pending_matches["utc_date"] = pd.to_datetime(pending_matches["utc_date"], errors="coerce")
        next_row = pending_matches.sort_values("utc_date").iloc[0]
        next_match = _format_match(next_row)
        next_match_detail = str(next_row["utc_date"]) if pd.notna(next_row["utc_date"]) else ""

    total_matches = len(matches_df)
    finished_count = len(finished_matches)
    completion_rate = (finished_count / total_matches * 100) if total_matches else 0.0

    return {
        "leader": {
            "label": "Lider de la competicion",
            "value": leader["team"],
            "detail": f"{int(leader['points'])} puntos",
        },
        "top_attack": {
            "label": "Equipo mas goleador",
            "value": top_attack["team"],
            "detail": f"{int(top_attack['goals_for'])} goles",
        },
        "best_defense": {
            "label": "Mejor defensa",
            "value": best_defense["team"],
            "detail": f"{int(best_defense['goals_against'])} goles encajados",
        },
        "goals_per_match": {
            "label": "Promedio de goles",
            "value": f"{goals_per_match:.2f}",
            "detail": "por partido finalizado",
        },
        "highest_scoring_match": {
            "label": "Partido con mas goles",
            "value": highest_scoring_match,
            "detail": highest_scoring_detail,
        },
        "next_match": {
            "label": "Proximo partido",
            "value": next_match,
            "detail": next_match_detail,
        },
        "completion_rate": {
            "label": "Partidos finalizados",
            "value": f"{finished_count}/{total_matches}",
            "detail": f"{completion_rate:.1f}% completado",
        },
        "pending_matches": {
            "label": "Partidos pendientes",
            "value": str(len(pending_matches)),
            "detail": "por disputar o actualizar",
        },
    }
