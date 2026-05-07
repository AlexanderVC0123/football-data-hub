import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.read_queries import (
    load_competitions,
    load_last_sync_run,
    load_matches_by_team,
    load_standings,
    load_teams,
)


def load_combined_matches(competition_id: int | None, *team_names: str):
    frames = [
        load_matches_by_team(team_name, competition_id=competition_id)
        for team_name in team_names
        if team_name
    ]
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(
        subset=["matchday", "utc_date", "home_team", "away_team"],
        keep="first",
    )


__all__ = [
    "load_competitions",
    "load_last_sync_run",
    "load_standings",
    "load_teams",
    "load_matches_by_team",
    "load_combined_matches",
]
