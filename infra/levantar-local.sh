#!/bin/bash
# Levanta en local los dos servidores (público y privado), simulando las dos VMs
# de AWS, para poder verificar la infraestructura sin desplegar nada.
#
# Uso:  ./infra/levantar-local.sh   &&   ./infra/verificar-local.sh
#
# Al terminar, `./infra/restaurar-desarrollo.sh` devuelve el entorno de siempre.
#
# TU BASE DE DATOS DE DESARROLLO NO SE TOCA: los compose de producción corren en
# su propio proyecto de Compose (`torneos-prod`), con volúmenes y contenedores
# aparte. El stack de desarrollo solo se PARA (para liberar los puertos), no se
# borra; sus datos siguen ahí cuando lo vuelvas a levantar.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env.produccion.local"
PRIVADO="docker compose --env-file $ENV_FILE -f docker-compose.privado.yml"
PUBLICO="docker compose --env-file $ENV_FILE -f docker-compose.publico.yml"

echo "==> Preparando variables de producción para la prueba (no toca tu .env)"
# Este fichero es una copia de tu .env (con SECRET_KEY y contraseñas dentro). El
# patrón `.env.*` de .gitignore lo mantiene fuera del repositorio.
if [ ! -f "$ENV_FILE" ]; then
    cp .env "$ENV_FILE"
    cat >> "$ENV_FILE" <<'EOF'

# Solo para la prueba local. En AWS estos valores se generan de verdad:
#   openssl rand -base64 24
DB_ADMIN_USER=torneos_admin
DB_ADMIN_PASSWORD=admin_local_test
DB_APP_USER=torneos_app
DB_APP_PASSWORD=app_local_test
EOF
fi

echo "==> Red privada (simula la red interna de la VPC)"
docker network create torneos_privada 2>/dev/null || true

echo "==> Certificado autofirmado"
./infra/nginx/generar-certificado.sh localhost

# Solo `down`, NUNCA `down -v`: para los contenedores de desarrollo y libera los
# puertos (entre ellos el 5432, que si no haría fallar la comprobación 9), pero
# deja intactos el volumen y los datos de tu base de desarrollo.
echo "==> Parando el stack de desarrollo (libera los puertos; no borra nada)"
docker compose down 2>/dev/null || true

echo "==> Servidor PRIVADO (API x2, panel, Postgres)"
$PRIVADO up -d --build

echo "==> Migraciones (contenedor efímero: es el único con credenciales de admin)"
$PRIVADO --profile migraciones run --rm migraciones

echo "==> Servidor PÚBLICO (nginx)"
$PUBLICO up -d

# nginx resuelve las direcciones de los backends UNA vez, al arrancar, y las
# cachea. Si los contenedores de la API se recrearon, sus IPs cambiaron y nginx
# seguiría golpeando las viejas (502). Reiniciarlo lo obliga a resolverlas de
# nuevo. En AWS esto no ocurre: los upstreams son la IP fija de la EC2 privada.
echo "==> Reiniciando nginx para que resuelva las IPs actuales de los backends"
$PUBLICO restart nginx

echo "==> Esperando a que la API responda a través de nginx"
until curl -sk -o /dev/null https://localhost/api/health 2>/dev/null; do sleep 1; done

echo
echo "Listo. Ahora:  ./infra/verificar-local.sh"
