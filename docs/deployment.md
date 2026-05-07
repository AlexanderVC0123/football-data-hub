# Deployment Notes

Esta guia resume una ruta sencilla para llevar Football Data Hub a un entorno mas profesional.

## Web

Opcion recomendada para prototipo:

1. Crear una base PostgreSQL remota en Supabase, Neon, Railway o Render.
2. Configurar las variables de entorno en el hosting elegido.
3. Desplegar `streamlit_app/dashboard.py`.
4. Usar `APP_ENV=production` y `ENABLE_MANUAL_SYNC=false`.

Variables necesarias:

```env
APP_ENV=production
ENABLE_MANUAL_SYNC=false
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
FOOTBALL_API_URL=https://api.football-data.org/v4
FOOTBALL_API_KEY=
```

## Sincronizacion Automatica

La web no deberia depender de pulsar un boton manual en produccion.

Opciones:
- GitHub Actions programado;
- cron en un servidor;
- worker en Render/Railway;
- Programador de tareas de Windows para prototipo local.

Comando recomendado:

```bash
python run.py --all
```

## Desktop

Para prototipo instalable:

```bash
pyinstaller --onefile --windowed desktop_app/main.py
```

Luego se puede crear un instalador con Inno Setup.

## Recomendacion De Produccion

- Una unica base PostgreSQL remota.
- Web y desktop leyendo la misma base.
- Sincronizacion ejecutada por una tarea separada.
- `ENABLE_MANUAL_SYNC=false` para usuarios finales.
