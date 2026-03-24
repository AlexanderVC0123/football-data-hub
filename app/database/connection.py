import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_connection():
    """Establece una conexión a la base de datos PostgreSQL utilizando las variables de entorno."""

    connection = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    return connection

def test_connection():
    """Prueba la conexión a la base de datos y devuelve un mensaje de éxito o error."""

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print(f"Conexión exitosa a la base de datos. Versión: {version[0]}")
        print("Version del servidor: ", version[0])

        cursor.close()
        connection.close()
    
    except Exception as error:
        print("Error al conectar con PostgresSQL")
        print("Detalle del error: ", error)

def execute_schema():
    "Lee el archivo schema.sql y ejecuta su contenido para crear las tablas en la base de datos."

    try:
        connection = get_connection()
        cursor = connection.cursor()

        #Abrimos el archivo sql en modo lectura
        with open("sql/schema.sql", "r", encoding="utf-8") as sql_file:
            sql_script = sql_file.read()

        #Ejecutamos el script sql
        cursor.execute(sql_script)

        #Confirmamos los cambios en la base de datos
        connection.commit()

        print("Tablas creadas correctamente desde el archivo schema.sql")

        cursor.close()
        connection.close()
    
    except Exception as error:
        print("Error al ejecutar schema.sql")
        print("Detalle del error: ", error)