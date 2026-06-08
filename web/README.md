# Panel de administración (Flask)

Panel web que **consume la API**. Inicia sesión contra la API, guarda el JWT en
la sesión de Flask y lo reenvía como `Bearer` en cada llamada. Está pensado para
el rol **superadmin**.

## Funcionalidad

- **Login / logout** contra `/auth/login` (solo deja entrar a administradores).
- **Dashboard**: estado de la API y de la base de datos, conteo de torneos.
- **Torneos**: listar y crear (consume `GET/POST /torneos`).
- **Tabla de posiciones**: por torneo (`GET /estadisticas/torneos/{id}/tabla`).

## Cómo probarlo

Con todo el entorno arriba (`docker compose up --build`) y tras crear las tablas
y cargar el seed:

```bash
docker compose exec api alembic upgrade head     # si aún no creaste las tablas
docker compose exec api python -m app.seed       # crea el admin de prueba
```

Abre **http://localhost:5000** e inicia sesión con:

```
superadmin@demo.com / admin1234
```

## Cómo funciona la conexión con la API

- La URL de la API se toma de la variable `API_URL` del `.env`
  (por defecto `http://api:8000`, el nombre del servicio en docker-compose).
- El token JWT se guarda en `session["token"]`. Si la API responde `401`
  (token expirado), el panel cierra la sesión y te manda al login.

## Notas

- El formulario de "nuevo torneo" pide el **ID de sede** como número (la sede #1
  la crea el seed). El paso siguiente natural sería añadir un endpoint
  `GET /sedes` en la API para mostrar un desplegable de sedes por nombre.
- El panel **no** se conecta a PostgreSQL directamente: todo pasa por la API.
  Por eso sus dependencias son mínimas (Flask + requests).
