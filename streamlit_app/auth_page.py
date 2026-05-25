from html import escape

import streamlit as st

from app.auth.auth_service import login_supabase


def inicializar_sesion():
    """
    Inicializa las variables de sesión que usa Streamlit mientras la app está abierta.
    """

    if "logueado" not in st.session_state:
        st.session_state.logueado = False

    if "usuario" not in st.session_state:
        st.session_state.usuario = None


def mostrar_login_header():
    """
    Muestra un login compacto dentro de la cabecera del dashboard.
    """

    with st.popover("Acceder", use_container_width=True):
        with st.form("login_form", clear_on_submit=False):

            email = st.text_input(
                "Email",
                placeholder="usuario@email.com",
                label_visibility="collapsed",
            )

            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Contraseña",
                label_visibility="collapsed",
            )

            login_button = st.form_submit_button("Iniciar sesión", use_container_width=True,)

        if not login_button:
            return

        if email == "" or password == "":
            st.warning("Introduce email y contraseña")
            return

        respuesta = login_supabase(email, password)

        if respuesta is not None and respuesta.user is not None:
            st.session_state.logueado = True
            st.session_state.usuario = respuesta.user
            st.success("Login correcto")
            st.rerun()

        st.error("Email o contraseña incorrecto")


def mostrar_usuario_header():
    """
    Muestra el usuario conectado dentro de un popover y el botón de cerrar sesión.
    """

    email = ""
    if st.session_state.usuario is not None:
        email = escape(st.session_state.usuario.email)

        short_label = email.split("@")[0] if email else "Sesión"
    
    with st.popover(f"{short_label}", use_container_width=True):

        st.markdown(
            f"""
            <div class="fdh-user-box">
                <h3>Sesión iniciada</h3>
                <div class="fdh-user-email">{email}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Cerrar sesión", key="logout_button", use_container_width=True):
            cerrar_sesion()


def cerrar_sesion():
    """
    Cierra sesión y limpia el usuario guardado en memoria.
    """

    st.session_state.logueado = False
    st.session_state.usuario = None
    st.rerun()
