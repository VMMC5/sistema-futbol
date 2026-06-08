# Base de datos y migraciones (Alembic)

Las tablas **no** se crean a mano. Se definen en `app/models.py` y se aplican
mediante migraciones de Alembic, para que todo el equipo tenga la misma
estructura con los mismos comandos.

Todos los comandos se ejecutan **dentro del contenedor de la API**, que ya
tiene Python y las dependencias. Primero levanta el entorno:

```bash
docker compose up --build
```

## 1. Crear la primera migración (genera las 14 tablas)

En otra terminal:

```bash
docker compose exec api alembic revision --autogenerate -m "tablas iniciales"
```

Alembic compara los modelos contra la base de datos (vacía) y escribe un
archivo en `api/migrations/versions/`. **Revísalo** antes de aplicarlo: debe
contener un `op.create_table(...)` por cada una de las 14 entidades.

## 2. Aplicar la migración

```bash
docker compose exec api alembic upgrade head
```

Esto crea las tablas en PostgreSQL. Comprueba en `http://localhost:8000/health`
que sigue respondiendo `base_de_datos: ok`.

## 3. Cargar datos de prueba

```bash
docker compose exec api python -m app.seed
```

Inserta los 4 roles, una sede y un usuario de cada rol.

## Flujo cuando cambien el modelo más adelante

Cada vez que alguien edite `app/models.py` (agregar una columna, una tabla...):

```bash
docker compose exec api alembic revision --autogenerate -m "describe el cambio"
docker compose exec api alembic upgrade head
```

El archivo de migración generado **se sube a Git** (forma parte del repo). Así,
cuando otro compañero hace `git pull`, solo corre `alembic upgrade head` y su
base de datos queda igual a la de todos. **Nunca** cambien las tablas a mano en
PostgreSQL: siempre vía migración.

## Errores comunes

- *"Target database is not up to date"* al autogenerar: aplica primero
  `alembic upgrade head` y vuelve a intentar.
- La migración sale vacía: revisa que `app/models.py` esté importado en
  `migrations/env.py` (ya lo está) y que el modelo nuevo herede de `Base`.
