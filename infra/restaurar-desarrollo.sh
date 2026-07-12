#!/bin/bash
# Devuelve el entorno de DESARROLLO de siempre, tras haber probado la
# infraestructura de producción en local.
#
# Uso:  ./infra/restaurar-desarrollo.sh
#
# La prueba de producción corre en su PROPIO proyecto de Docker Compose
# (`torneos-prod`), con sus propios volúmenes y nombres de contenedor. Tu base de
# datos de desarrollo no se toca en ningún momento: aquí solo se borra la base de
# la prueba y se vuelve a levantar el stack de siempre, con sus datos intactos.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env.produccion.local"

echo "==> Parando los servidores de la prueba y borrando SUS volúmenes"
# `down -v` borra los volúmenes del proyecto `torneos-prod` (torneos-prod_pgdata,
# que tiene los usuarios y datos de producción, y torneos-prod_uploads).
# El volumen de desarrollo (`sistema-futbol_pgdata`) es otro y NO se toca.
docker compose --env-file "$ENV_FILE" -f docker-compose.publico.yml down -v 2>/dev/null || true
docker compose --env-file "$ENV_FILE" -f docker-compose.privado.yml down -v 2>/dev/null || true

rm -f "$ENV_FILE"

echo "==> Levantando el stack de desarrollo"
# No hace falta re-migrar ni re-sembrar: la base de desarrollo sigue donde estaba,
# con sus migraciones y sus datos demo.
docker compose up -d

echo "==> Esperando a la API"
until curl -sf -o /dev/null http://localhost:8000/health 2>/dev/null; do sleep 1; done

echo
echo "Entorno de desarrollo restaurado (con tus datos de siempre):"
echo "  API   -> http://localhost:8000/docs"
echo "  Panel -> http://localhost:5000"
