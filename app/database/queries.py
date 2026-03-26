from app.database.connection import get_connection

def insert_competition(competition_data: dict):
    """Inserta una competición en la base de datos. si ya existe por api_id. No la duplicará."""

    query = """
        INSERT INTO competitions (api_id, name, code, country_name, type, emblem_url)
        VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (api_id) DO NOTHING;
        """
    values = (
        competition_data.get("id"),
        competition_data.get("name"),
        competition_data.get("code"),
        competition_data.get("area", {}).get("name"),
        competition_data.get("type"),
        competition_data.get("emblem")
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
    
    finally:
        cursor.close()
        connection.close()

def insert_team(team_data: dict):
    """Inserta un equipo en la base de datos, Si ya existe por api_id, no lo duplica."""

    query = """ INSERT INTO teams(api_id, name, short_name, tla, founded, venue, website, club_colors, address, crest_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (api_id) DO NOTHING
    """

    values = (
        team_data.get("id"),
        team_data.get("name"),
        team_data.get("short_name"),
        team_data.get("tla"),
        team_data.get("founded"),
        team_data.get("venue"),
        team_data.get("website"),
        team_data.get("clubColors"),
        team_data.get("address"),
        team_data.get("crest"),
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_competition_db_id_by_api_id(api_id: int):
    query = "SELECT id FROM competitions WHERE api_id = %s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, (api_id))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()

def get_team_db_id_by_api_id(api_id: int):
    query = "SELECT id FROM teams WHERE api_id=%s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, (api_id))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()

def get_season_db_id_by_api_id(api_id: int):
    query="SELECT id FROM seasons WHERE api_id=%s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query,(api_id))
        result = cursor.fetchone
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()

def insert_season(season_data: dict, competition_api_id: int):
    """Inserta una temporada asociada a una competición"""
    competition_id = get_competition_db_id_by_api_id(competition_api_id)

    if competition_id is None:
        print("No se encontro la competición con api_id={competition_api_id}")
        return
    
    winner_api = season_data.get("winner",{})
    winner_api_id = winner_api.get("id") if winner_api else None
    winner_team_id = get_team_db_id_by_api_id(winner_api_id) if winner_api_id else None

    query = """INSERT INTO seasons (api_id, competition_id, start_date, end_date, current_matchday, winner_team_id)
                VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (api_id) DO NOTHING
            """

    values = (
        season_data.get("id"),
        competition_id,
        season_data.get("startDate"),
        season_data.get("endDate"),
        season_data.get("current_matchday"),
        winner_team_id
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_standing_row(standing_row: dict, season_api_id: dict, competition_api_id: int):
    "Inserta una fila de clasificación"
    competition_id = get_competition_db_id_by_api_id(competition_api_id)
    season_id = get_season_db_id_by_api_id(season_api_id)

    team_api_id = standing_row.get("team",{}).get("id")
    team_id = get_team_db_id_by_api_id(team_api_id)

    if not competition_id or not season_id or not team_id:
        print(f"No se pudo insertar standing para team_api_id={team_api_id}")
        return
    
    query="""
        INSERT INTO standings(
            competition_id, season_id, team_id, position, played_games, won, draw, lost, points, goals_for,
            goals_against, goal_difference, form
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (season_id, team_id) DO NOTHING
        """
    
    values = (
        competition_id,
        season_id,
        team_id,
        standing_row.get("position"),
        standing_row.get("played_games"),
        standing_row.get("won"),
        standing_row.get("draw"),
        standing_row.get("lost"),
        standing_row.get("points"),
        standing_row.get("goals_for"),
        standing_row.get("goals_against"),
        standing_row.get("goal_difference"),
        standing_row.get("form")
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()