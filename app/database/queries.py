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
    