import os
from dotenv import load_dotenv
from supabase import create_client

#Cargamos las variables del archivo .env
load_dotenv()

def crear_cliente_supabase():
    """
    Crea el cliente usando las variables del archivo .env
    """

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if url is None or key is None:
        print("Los datos de las variables de .env son incorrectos o faltan datos.")
        return None
    
    return create_client(url, key)

def login_supabase(email, password):
    """
    Inicia sesión en Supabase con email y contraseña.
    Si el login es correcto, devuelve los datos del usuario.
    Si falla, devuelve None.
    """

    supabase = crear_cliente_supabase()

    if supabase is None:
        return None
    
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return res
    except Exception as error:
        print("Error al iniciar sesión con supabase", error)
        return None