from app.database.connection import test_connection, execute_schema

if __name__ == "__main__":
    print("Iniciando Football Data Hub...")
    test_connection()
    execute_schema()