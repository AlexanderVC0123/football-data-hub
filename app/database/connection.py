import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

load_dotenv(ENV_PATH)

REQUIRED_DB_ENV_VARS = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")


def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Falta la variable de entorno requerida: {var_name}")
    return value


def get_connection():
    """Establece una conexion a PostgreSQL usando variables de entorno."""

    missing_vars = [var_name for var_name in REQUIRED_DB_ENV_VARS if not os.getenv(var_name)]
    if missing_vars:
        raise ValueError(
            "Faltan variables de entorno requeridas para PostgreSQL: "
            + ", ".join(missing_vars)
        )

    return psycopg2.connect(
        dbname=get_required_env("DB_NAME"),
        user=get_required_env("DB_USER"),
        password=get_required_env("DB_PASSWORD"),
        host=get_required_env("DB_HOST"),
        port=int(get_required_env("DB_PORT")),
    )


def test_connection():
    """Prueba la conexion a la base de datos e imprime el resultado."""

    try:
        connection = get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()

                print(f"Conexion exitosa a la base de datos. Version: {version[0]}")
            finally:
                cursor.close()
        finally:
            connection.close()

    except Exception as error:
        print("Error al conectar con PostgreSQL")
        print("Detalle del error: ", error)


def execute_schema(connection=None):
    """
        Lee schema.sql y ejecuta su contenido para crear las tablas.
        Puede usar una conexión existente o crear una nueva
    """
    close_connection = False

    if connection is None:
        connection = get_connection()
        close_connection = True
    
    cursor = connection.cursor()

    
    try:
        with SCHEMA_PATH.open("r", encoding="utf-8") as sql_file:
                sql_script = sql_file.read()

        cursor.execute(sql_script)

        if close_connection:
            connection.commit()

        print("Tablas creadas correctamente desde el archivo schema.sql")

    except Exception as error:
        print("Error al ejecutar schema.sql")
        print("Detalle del error: ", error)
        raise error
                
    finally:
        cursor.close()
        if close_connection:
            connection.close()