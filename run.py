from app.database.connection import test_connection, execute_schema
from app.services.import_service import import_competitions, import_teams_by_competition

if __name__ == "__main__":
    print("Iniciando Football Data Hub...")
    test_connection()
    execute_schema()

    #Importar competiciones
    import_competitions()
    #Importar equipos de una competicion en este caso de LaLiga (PD)
    import_teams_by_competition("PD")