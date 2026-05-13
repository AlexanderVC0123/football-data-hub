import streamlit as st

from app.auth.auth_service import login_supabase


def inicializar_sesion():
    """
    Inicializa las variables de sesion que usa Streamlit mientras la app esta abierta.
    """

    if "logueado" not in st.session_state:
        st.session_state.logueado = False

    if "usuario" not in st.session_state:
        st.session_state.usuario = None


def mostrar_login():
    """
    Muestra la pagina de login y guarda el usuario si Supabase valida las credenciales.
    """

    inicializar_sesion()

    st.title("FOOTBALL DATA HUB")
    st.subheader("Inicio de sesion")

    email = st.text_input("Email")
    password = st.text_input("Contrasena", type="password")

    if st.button("Iniciar sesion"):
        if email == "" or password == "":
            st.warning("Debes introducir email y contrasena")
            return

        respuesta = login_supabase(email, password)

        if respuesta is not None and respuesta.user is not None:
            st.session_state.logueado = True
            st.session_state.usuario = respuesta.user
            st.success("Login correcto")
            st.rerun()

        st.error("Email o contrasena incorrectos")


def cerrar_sesion():
    """
    Cierra sesion y limpia el usuario guardado en memoria.
    """

    st.session_state.logueado = False
    st.session_state.usuario = None
    st.rerun()


def mostrar_sidebar_sesion():
    """
    Muestra los datos de la sesión en la barra lateral del dashboard.
    """

    with st.sidebar:
        st.write("### Sesion")

        if st.session_state.usuario is not None:
            st.write(st.session_state.usuario.email)

        if st.button("Cerrar sesion"):
            cerrar_sesion()
