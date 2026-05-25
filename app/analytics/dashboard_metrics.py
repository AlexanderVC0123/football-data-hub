from __future__ import annotations

import pandas as pd


def _format_match(row: pd.Series) -> str:
    return f"{row['home_team']} vs {row['away_team']}"


def calculate_competition_kpis(standings_df: pd.DataFrame, matches_df: pd.DataFrame) -> dict:
    """Calcula indicadores principales para resumir una competición.

    Cada KPI devuelve label, value, detail y opcionalmente delta_numeric (con signo)
    cuando una comparación tiene sentido para colorear verde/rojo en la UI.
    """

    standings_sorted = standings_df.sort_values("position").reset_index(drop=True)
    leader = standings_sorted.iloc[0]
    second = standings_sorted.iloc[1] if len(standings_sorted) > 1 else None

    # Goleador y mejor defensa: comparamos con el 2º del ranking correspondiente
    attack_sorted = standings_df.sort_values("goals_for", ascending=False).reset_index(drop=True)
    top_attack = attack_sorted.iloc[0]
    second_attack = attack_sorted.iloc[1] if len(attack_sorted) > 1 else None

    defense_sorted = standings_df.sort_values("goals_against", ascending=True).reset_index(drop=True)
    best_defense = defense_sorted.iloc[0]
    second_defense = defense_sorted.iloc[1] if len(defense_sorted) > 1 else None

    # Solo usamos partidos finalizados para medias de goles
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
        if pd.notna(next_row["utc_date"]):
            next_match_detail = next_row["utc_date"].strftime("%d/%m/%Y")

    total_matches = len(matches_df)
    finished_count = len(finished_matches)
    completion_rate = (finished_count / total_matches * 100) if total_matches else 0.0

    # === Cálculo de deltas reales ===
    # Líder: ventaja en puntos sobre el 2º
    leader_delta = None
    leader_detail = f"{int(leader['points'])} puntos"
    if second is not None:
        gap = int(leader["points"]) - int(second["points"])
        if gap > 0:
            leader_delta = gap
            leader_detail = f"{int(leader['points'])} pts · ventaja sobre el 2º"

    # Goleador: diferencia de goles sobre el 2º atacante
    attack_delta = None
    attack_detail = f"{int(top_attack['goals_for'])} goles"
    if second_attack is not None:
        gap = int(top_attack["goals_for"]) - int(second_attack["goals_for"])
        if gap > 0:
            attack_delta = gap
            attack_detail = f"{int(top_attack['goals_for'])} goles · ventaja sobre el 2º"

    # Mejor defensa: cuántos goles menos encaja que el 2º defensor (delta NEGATIVO en goles
    # es BUENO defensivamente, pero queremos que Streamlit lo pinte verde → invertimos signo)
    defense_delta = None
    defense_detail = f"{int(best_defense['goals_against'])} goles encajados"
    if second_defense is not None:
        gap = int(second_defense["goals_against"]) - int(best_defense["goals_against"])
        if gap > 0:
            defense_delta = gap  # positivo = mejor que el 2º
            defense_detail = f"{int(best_defense['goals_against'])} encajados · diferencia con el 2º"

    return {
        "leader": {
            "label": "Líder de la competición",
            "value": leader["team"],
            "detail": leader_detail,
            "delta_numeric": leader_delta,
        },
        "top_attack": {
            "label": "Máximo goleador",
            "value": top_attack["team"],
            "detail": attack_detail,
            "delta_numeric": attack_delta,
        },
        "best_defense": {
            "label": "Mejor defensa",
            "value": best_defense["team"],
            "detail": defense_detail,
            "delta_numeric": defense_delta,
        },
        "goals_per_match": {
            "label": "Promedio de goles",
            "value": f"{goals_per_match:.2f}",
            "detail": "por partido finalizado",
            "delta_numeric": None,
        },
        "highest_scoring_match": {
            "label": "Partido con más goles",
            "value": highest_scoring_match,
            "detail": highest_scoring_detail,
            "delta_numeric": None,
        },
        "next_match": {
            "label": "Próximo partido",
            "value": next_match,
            "detail": next_match_detail,
            "delta_numeric": None,
        },
        "completion_rate": {
            "label": "Partidos finalizados",
            "value": f"{finished_count}/{total_matches}",
            "detail": f"{completion_rate:.1f}% completado",
            "delta_numeric": None,
        },
        "pending_matches": {
            "label": "Partidos pendientes",
            "value": str(len(pending_matches)),
            "detail": "por disputar o actualizar",
            "delta_numeric": None,
        },
    }