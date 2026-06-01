# Football Data Hub

> Sistema de análisis y predicción de competiciones de fútbol. Por el momento de las 5 principales ligas europeas.

Proyecto de Fin de Grado · CFGS Desarrollo de Aplicaciones Multiplataforma
IES Ítaca · Curso 2024-2026 · 
**Alexander Valladares Cueva**

**Web desplegada**: https://fdhcenter.streamlit.app


> **Nota académica:** la autenticación es obligatoria en esta versión para
> demostrar el sistema de login implementado con Supabase Auth. En futuras
> versiones, la web será accesible sin login y la autenticación se reservará
> para funcionalidades avanzadas (preferencias, estadísticas personalizadas,
> equipos favoritos).

---

## ¿Qué es?

Una plataforma que automatiza la extracción, almacenamiento y análisis de
datos de las cinco principales ligas europeas, con dos interfaces (web y
escritorio) que comparten la misma lógica de negocio y un modelo de
predicción basado en el modelo de Poisson.

---

## Características principales

- Sincronización automática diaria desde la API football-data.org
- Aplicación web con cinco pestañas analíticas (Streamlit)
- Aplicación de escritorio instalable como ejecutable (CustomTkinter + PyInstaller)
- Modelo de predicción Poisson con probabilidades 1X2, xG y marcadores probables
- Autenticación de usuarios con Supabase Auth y Row-Level Security
- CI/CD y pruebas automatizadas con GitHub Actions

---

## Stack

**Backend** · Python 3.12 · PostgreSQL · Supabase · pandas · scipy
**Frontend web** · Streamlit · Plotly · CSS personalizado
**Frontend desktop** · CustomTkinter · PyInstaller
**Infraestructura** · GitHub Actions · Streamlit Community Cloud
**Pruebas** · pytest 

---

## Instalación

### Requisitos

- Python 3.10 o superior
- Git
- Cuenta gratuita en [football-data.org](https://www.football-data.org)
- Cuenta gratuita en [Supabase](https://supabase.com)

### Pasos

````bash
# 1. Clonar el repositorio
git clone https://github.com/AlexanderVC0123/football-data-hub.git
cd football-data-hub

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar credenciales
cp .env.example .env            # Editar con tus credenciales

# 5. Crear el esquema en la BD
# Ejecutar el contenido de sql/schema.sql en Supabase o PostgreSQL local

# 6. Sincronizar datos por primera vez
python run.py
````

-----

## Uso

### Aplicación web

````bash
streamlit run streamlit_app/dashboard.py
````

### Aplicación de escritorio

````bash
python desktop_app/main.py
````

### Generar ejecutable de escritorio

````bash
pyinstaller football_data_hub.spec
````

El archivo `FootballDataHub.exe` se genera en `dist/`.

### Usuario de prueba (web desplegada)

````
URL:        https://fdhcenter.streamlit.app
Email:      admin@fdh.com
Contraseña: admin
````

-----

## Pruebas

````bash
pytest -v
````

15 pruebas que cubren configuración, cliente de la API, cálculo de KPIs,
análisis de partidos y operaciones de base de datos.

-----

## Documentación

El proyecto cuenta con una memoria técnica completa disponible en el
repositorio, donde se detallan arquitectura, decisiones de diseño,
implementación, despliegue y reflexión final.

-----

## Autor

**Alexander Valladares Cueva** · [@AlexanderVC0123](https://github.com/AlexanderVC0123)

Tutor: **Alejandro Fernández Burgo**

IES Ítaca · Mayo 2026
