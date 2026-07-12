#!/bin/bash
# Devuelve el entorno de DESARROLLO de siempre, tras haber probado la
# infraestructura de producción en local.
#
# Uso:  ./infra/restaurar-desarrollo.sh
#
# Ojo: la prueba de producción recrea la base de datos desde cero (el script de
# init de Postgres solo corre con un volumen nuevo). Este script vuelve a
# aplicar las migraciones y a sembrar los datos demo de desarrollo.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env.produccion.local"

echo "==> Parando los servidores de la prueba"
docker compose --env-file "$ENV_FILE" -f docker-compose.publico.yml down 2>/dev/null || true
docker compose --env-file "$ENV_FILE" -f docker-compose.privado.yml down 2>/dev/null || true

echo "==> Borrando la base de la prueba (tiene los usuarios de producción)"
docker volume rm sistema-futbol_pgdata 2>/dev/null || true

rm -f "$ENV_FILE"

echo "==> Levantando el stack de desarrollo"
docker compose up -d

echo "==> Esperando a la API"
until curl -sf -o /dev/null http://localhost:8000/health 2>/dev/null; do sleep 1; done

echo "==> Migraciones y datos demo"
docker compose exec -T api alembic upgrade head >/dev/null 2>&1
docker compose exec -T api python -m app.seed

echo
echo "Entorno de desarrollo restaurado:"
echo "  API   -> http://localhost:8000/docs"
echo "  Panel -> http://localhost:5000"
