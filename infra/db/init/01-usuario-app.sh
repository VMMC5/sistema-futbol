#!/bin/bash
# Crea el usuario con el que la API se conecta en runtime.
#
# Postgres ejecuta este script UNA sola vez, al inicializar un volumen nuevo.
# Por eso la base de producción se crea desde cero y el entorno local no se toca.
#
# El usuario NO recibe CREATE sobre el esquema: no puede crear ni alterar tablas.
# Eso lo hacen las migraciones, que corren con el usuario admin (POSTGRES_USER).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE "${DB_APP_USER}" LOGIN PASSWORD '${DB_APP_PASSWORD}';

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${DB_APP_USER}";
    GRANT USAGE ON SCHEMA public TO "${DB_APP_USER}";

    -- La clave del montaje: las tablas que Alembic cree DESPUÉS heredan estos
    -- permisos automáticamente. Sin esto habría que re-otorgar permisos tras
    -- cada migración, y alguien lo olvidaría.
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${DB_APP_USER}";

    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO "${DB_APP_USER}";
EOSQL

echo "Usuario limitado '${DB_APP_USER}' creado (sin permisos de DDL)."
