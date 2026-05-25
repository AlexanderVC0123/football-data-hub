# Football Data Hub

Football Data Hub es una plataforma de análisis futbolístico con app web y app de escritorio. El proyecto consume datos desde una API externa, los guarda en PostgreSQL y permite explorar clasificaciones, partidos, equipos, comparativas y predicciones iniciales basadas en un modelo Poisson simple.

## Estado Del Proyecto

Fase actual: MVP tecnico avanzado.

Incluye:
- sincronización desde football-data.org;
- PostgreSQL como base central;
- web con Streamlit;
- app desktop con CustomTkinter;
- filtros por competición;
- historico de sincronizaciones;
- relacion competición-equipo-temporada;
- predicción de partidos con Poisson;
- tests automaticos con pytest.

## Tecnologias

- Python
- PostgreSQL
- Pandas
- psycopg2
- Streamlit
- CustomTkinter
- Plotly
- Pytest
- python-dotenv

## Estructura

```text
app/
  analytics/        Motor de analisis y predicción
  api/              Cliente de football-data.org
  database/         Conexion, queries y lecturas
  services/         sincronización API -> PostgreSQL

desktop_app/        Aplicacion de escritorio
streamlit_app/      Dashboard web
sql/                Esquema y consultas SQL
tests/              Tests automaticos
run.py              Entrada para sincronizar datos
```

## Configuracion

1. Crea un entorno virtual:

```bash
python -m venv venv
```

2. Activalo en Windows:

```bash
venv\Scripts\activate
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

4. Crea tu archivo `.env` a partir de `.env.example`:

```bash
copy .env.example .env
```

5. Completa tus variables:

```env
APP_ENV=development
ENABLE_MANUAL_SYNC=true

DB_NAME=football_data_hub
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

FOOTBALL_API_URL=https://api.football-data.org/v4
FOOTBALL_API_KEY=your_api_key
```

En produccion se recomienda:

```env
APP_ENV=production
ENABLE_MANUAL_SYNC=false
```

## Base De Datos

El esquema se crea automaticamente al arrancar la web, la app desktop o la sincronización.

Tambien puedes ejecutar:

```bash
venv\Scripts\python.exe run.py --competition PD
```

Las tablas principales son:
- `competitions`
- `teams`
- `seasons`
- `competition_teams`
- `standings`
- `matches`
- `sync_runs`

## Sincronización De Datos

Sincronizar una competición:

```bash
venv\Scripts\python.exe run.py --competition PD
```

Sincronizar varias:

```bash
venv\Scripts\python.exe run.py --competitions PD PL SA
```

Sincronizar las competiciones por defecto:

```bash
venv\Scripts\python.exe run.py --all
```

Competiciones por defecto:

```text
PD, PL, SA, BL1, FL1
```

Cada sincronización queda registrada en `sync_runs` con estado `SUCCESS` o `FAILED`.

## Ejecutar La Web

```bash
venv\Scripts\python.exe -m streamlit run streamlit_app/dashboard.py
```

URL local:

```text
http://localhost:8501
```

## Ejecutar La App Desktop

```bash
venv\Scripts\python.exe desktop_app/main.py
```

## Tests

```bash
venv\Scripts\python.exe -m pytest
```

## Automatizacion Con GitHub Actions

El proyecto incluye dos workflows:

- `.github/workflows/ci.yml`: ejecuta tests en push y pull request.
- `.github/workflows/sync-data.yml`: sincroniza datos cada 6 horas y tambien permite ejecucion manual.

Para que `sync-data.yml` funcione, configura estos secrets en GitHub:

```text
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
FOOTBALL_API_URL
FOOTBALL_API_KEY
```

La sincronización programada ejecuta:

```bash
python run.py --all
```

Desde GitHub Actions tambien puedes lanzar una sincronización manual indicando competiciones:

```text
PD PL SA
```

## Despliegue Web

Para prototipo rapido:
- Streamlit Community Cloud;
- Render;
- Railway;
- Hugging Face Spaces.

Base de datos recomendada:
- Supabase PostgreSQL;
- Neon;
- Railway PostgreSQL;
- Render PostgreSQL.

En despliegue, la web deberia conectarse a una base PostgreSQL remota y no mostrar controles manuales de sincronización:

```env
APP_ENV=production
ENABLE_MANUAL_SYNC=false
```

La sincronización de datos puede ejecutarse con:
- GitHub Actions programado;
- cron en servidor;
- tarea programada de Windows;
- worker separado.

## Desktop Instalable

Para prototipo se puede empaquetar con PyInstaller:

```bash
pyinstaller --onefile --windowed desktop_app/main.py
```

Despues se puede crear un instalador con Inno Setup.

## Roadmap

- Mejorar la UI web con vistas por equipo y partido.
- Preparar despliegue con base de datos remota.
- Crear workflow automatico de sincronización.
- Empaquetar desktop como `.exe`.
- Mejorar predicción con local/visitante, forma reciente avanzada y mercados como over/under o ambos marcan.
