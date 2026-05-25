from app.database.connection import get_connection


def insert_sync_run(competition_code: str, started_at, status: str, message: str | None = None, connection=None):
    """Registra el resultado de una sincronización con la API."""

    query = """
        INSERT INTO sync_runs (competition_code, started_at, finished_at, status, message)
        VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s);
    """
    values = (competition_code, started_at, status, message)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def insert_competition(competition_data: dict, connection=None):
    """Inserta o actualiza una competicion usando el id de la API."""

    query = """
        INSERT INTO competitions (api_id, name, code, country_name, type, emblem_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (api_id) DO UPDATE
        SET
            name = EXCLUDED.name,
            code = EXCLUDED.code,
            country_name = EXCLUDED.country_name,
            type = EXCLUDED.type,
            emblem_url = EXCLUDED.emblem_url;
    """
    values = (
        competition_data.get("id"),
        competition_data.get("name"),
        competition_data.get("code"),
        competition_data.get("area", {}).get("name"),
        competition_data.get("type"),
        competition_data.get("emblem"),
    )

    close_connection = False

    if connection is None:
        connection = get_connection()
        close_connection = True
    
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        if close_connection:
            connection.commit()
    finally:
        cursor.close()
        if close_connection:
            connection.close()


def insert_team(team_data: dict):
    """Inserta o actualiza un equipo usando el id de la API."""

    query = """
        INSERT INTO teams(api_id, name, short_name, tla, founded, venue, website, club_colors, address, crest_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (api_id) DO UPDATE
        SET
            name = EXCLUDED.name,
            short_name = EXCLUDED.short_name,
            tla = EXCLUDED.tla,
            founded = EXCLUDED.founded,
            venue = EXCLUDED.venue,
            website = EXCLUDED.website,
            club_colors = EXCLUDED.club_colors,
            address = EXCLUDED.address,
            crest_url = EXCLUDED.crest_url;
    """

    values = (
        team_data.get("id"),
        team_data.get("name"),
        team_data.get("shortName"),
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


def get_competition_db_id_by_api_id(api_id: int, connection=None):
    query = "SELECT id FROM competitions WHERE api_id = %s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, (api_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()


def get_team_db_id_by_api_id(api_id: int, connection=None):
    query = "SELECT id FROM teams WHERE api_id=%s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, (api_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()


def get_season_db_id_by_api_id(api_id: int, connection=None):
    query = "SELECT id FROM seasons WHERE api_id=%s"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, (api_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()


def insert_competition_team(team_api_id: int, competition_api_id: int, season_api_id: int):
    """Relaciona un equipo con una competicion y una temporada."""

    competition_id = get_competition_db_id_by_api_id(competition_api_id)
    team_id = get_team_db_id_by_api_id(team_api_id)
    season_id = get_season_db_id_by_api_id(season_api_id)

    if not competition_id or not team_id or not season_id:
        print("No se pudo insertar relacion competition_teams")
        print(f"competition_api_id={competition_api_id} -> competition_id={competition_id}")
        print(f"team_api_id={team_api_id} -> team_id={team_id}")
        print(f"season_api_id={season_api_id} -> season_id={season_id}")
        return

    query = """
        INSERT INTO competition_teams (competition_id, team_id, season_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (competition_id, team_id, season_id) DO UPDATE
        SET updated_at = CURRENT_TIMESTAMP;
    """

    values = (competition_id, team_id, season_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def insert_season(season_data: dict, competition_api_id: int):
    """Inserta o actualiza una temporada asociada a una competicion."""

    competition_id = get_competition_db_id_by_api_id(competition_api_id)

    if competition_id is None:
        print(f"No se encontro la competicion con api_id={competition_api_id}")
        return

    winner_api = season_data.get("winner", {})
    winner_api_id = winner_api.get("id") if winner_api else None
    winner_team_id = get_team_db_id_by_api_id(winner_api_id) if winner_api_id else None

    query = """
        INSERT INTO seasons (api_id, competition_id, start_date, end_date, current_matchday, winner_team_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (api_id) DO UPDATE
        SET
            competition_id = EXCLUDED.competition_id,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            current_matchday = EXCLUDED.current_matchday,
            winner_team_id = EXCLUDED.winner_team_id;
    """

    values = (
        season_data.get("id"),
        competition_id,
        season_data.get("startDate"),
        season_data.get("endDate"),
        season_data.get("currentMatchday"),
        winner_team_id,
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_standing_row(standing_row: dict, competition_api_id: int, season_api_id: int):
    """Inserta o actualiza una fila de clasificación."""

    competition_id = get_competition_db_id_by_api_id(competition_api_id)
    season_id = get_season_db_id_by_api_id(season_api_id)

    team_api_id = standing_row.get("team", {}).get("id")
    team_id = get_team_db_id_by_api_id(team_api_id)

    if not competition_id or not season_id or not team_id:
        print("No se pudo insertar standing")
        print(f"competition_api_id={competition_api_id} -> competition_id={competition_id}")
        print(f"season_api_id={season_api_id} -> season_id={season_id}")
        print(f"team_api_id={team_api_id} -> team_id={team_id}")
        print(f"team_name={standing_row.get('team', {}).get('name')}")
        return

    query = """
        INSERT INTO standings(
            competition_id, season_id, team_id, position, played_games, won, draw, lost, points, goals_for,
            goals_against, goal_difference, form
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (season_id, team_id) DO UPDATE
        SET
            competition_id = EXCLUDED.competition_id,
            position = EXCLUDED.position,
            played_games = EXCLUDED.played_games,
            won = EXCLUDED.won,
            draw = EXCLUDED.draw,
            lost = EXCLUDED.lost,
            points = EXCLUDED.points,
            goals_for = EXCLUDED.goals_for,
            goals_against = EXCLUDED.goals_against,
            goal_difference = EXCLUDED.goal_difference,
            form = EXCLUDED.form,
            updated_at = CURRENT_TIMESTAMP;
    """

    values = (
        competition_id,
        season_id,
        team_id,
        standing_row.get("position"),
        standing_row.get("playedGames"),
        standing_row.get("won"),
        standing_row.get("draw"),
        standing_row.get("lost"),
        standing_row.get("points"),
        standing_row.get("goalsFor"),
        standing_row.get("goalsAgainst"),
        standing_row.get("goalDifference"),
        standing_row.get("form"),
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_match(match_data: dict, connection=None):
    """
    Inserta o actualiza un partido usando el id de la API.

    Si recibe una conexión, la reutiliza.
    Si no recibe conexión, crea una nueva.
    """

    close_connection = False

    # Si no recibimos conexión, creamos una nueva
    if connection is None:
        connection = get_connection()
        close_connection = True

    competition_api_id = match_data.get("competition", {}).get("id")
    season_api_id = match_data.get("season", {}).get("id")
    home_team_api_id = match_data.get("homeTeam", {}).get("id")
    away_team_api_id = match_data.get("awayTeam", {}).get("id")

    competition_id = get_competition_db_id_by_api_id(competition_api_id, connection)
    season_id = get_season_db_id_by_api_id(season_api_id, connection)
    home_team_id = get_team_db_id_by_api_id(home_team_api_id, connection)
    away_team_id = get_team_db_id_by_api_id(away_team_api_id, connection)

    if not competition_id or not season_id or not home_team_id or not away_team_id:
        print(f"No se puede ingresar el partido api_id={match_data.get('id')}")

        if close_connection:
            connection.close()

        return

    utc_date = match_data.get("utcDate")

    if not utc_date:
        print(f"Partido sin fecha api_id={match_data.get('id')}")

        if close_connection:
            connection.close()

        return

    score = match_data.get("score", {})
    full_time = score.get("fullTime", {})

    home_score = full_time.get("home")
    if home_score is None:
        home_score = full_time.get("homeTeam")

    away_score = full_time.get("away")
    if away_score is None:
        away_score = full_time.get("awayTeam")

    query = """
        INSERT INTO matches (
            api_id, competition_id, season_id, matchday, utc_date, status,
            home_team_id, away_team_id, home_score, away_score, winner,
            stage, group_name, last_updated
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (api_id) DO UPDATE
        SET
            competition_id = EXCLUDED.competition_id,
            season_id = EXCLUDED.season_id,
            matchday = EXCLUDED.matchday,
            utc_date = EXCLUDED.utc_date,
            status = EXCLUDED.status,
            home_team_id = EXCLUDED.home_team_id,
            away_team_id = EXCLUDED.away_team_id,
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            winner = EXCLUDED.winner,
            stage = EXCLUDED.stage,
            group_name = EXCLUDED.group_name,
            last_updated = EXCLUDED.last_updated;
    """

    values = (
        match_data.get("id"),
        competition_id,
        season_id,
        match_data.get("matchday"),
        utc_date,
        match_data.get("status"),
        home_team_id,
        away_team_id,
        home_score,
        away_score,
        score.get("winner"),
        match_data.get("stage"),
        match_data.get("group"),
        match_data.get("lastUpdated"),
    )

    cursor = connection.cursor()

    try:
        cursor.execute(query, values)

        # Solo hacemos commit si esta función ha creado la conexión
        if close_connection:
            connection.commit()

    finally:
        cursor.close()

        # Solo cerramos si esta función ha creado la conexión
        if close_connection:
            connection.close()
