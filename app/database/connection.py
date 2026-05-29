import os
import sys
import psycopg2

from pathlib import Path
from dotenv import load_dotenv

def resource_path(relative_path: str) -> Path:
    """
    Devuelve la ruta absoluta a un recurso.
    Sirve para desarrollo (script normal) como empaquetado con PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        #Ejecutandose desde un .exe empaquetado con PyInstaller
        return Path(sys._MEIPASS) / relative_path
    #Ejecutandose como script normal
    return Path(__file__).resolve().parents[2] / relative_path



PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = resource_path(".env")
SCHEMA_PATH = resource_path("sql/schema.sql")

load_dotenv(ENV_PATH)

REQUIRED_DB_ENV_VARS = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")


def get_env_var(var_name: str) -> str | None:
    """
    Se obtiene una variable de configuracion.
    Prioridad: variables de entorno (.env local) y si no existe,
    secrets de streamlit (st.secrets) en despliegue cloud
    """
    value = os.getenv(var_name)
    if value:
        return value
    
    #Fallback a st.secrets (para streamlit community cloud)
    try:
        import streamlit as st
        if var_name in st.secrets:
            return str(st.secrets[var_name])
    except Exception:
        pass

    return None

def get_required_env(var_name: str) -> str:
    value = get_env_var(var_name)
    if not value:
        raise ValueError(f"Falta la variable de entorno requerida: {var_name}")
    return value


def get_connection():
    """Establece una conexion a PostgreSQL usando variables de entorno."""

    missing_vars = [var_name for var_name in REQUIRED_DB_ENV_VARS if not get_env_var(var_name)]
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