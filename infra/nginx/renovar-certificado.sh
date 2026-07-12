#!/bin/bash
# Renueva el certificado de Let's Encrypt y recarga nginx con el nuevo.
#
# Uso (desde la raíz del repositorio, en la EC2 pública):
#   ./infra/nginx/renovar-certificado.sh <DOMINIO>
#
# Pensado para el cron diario (ver docs/DESPLIEGUE.md, sección 8). Certbot solo
# renueva de verdad si al certificado le quedan menos de 30 días; los demás días
# no hace nada y sale con éxito. Por eso puede correr a diario sin problema.
#
# Los TRES pasos son necesarios. Un cron que solo hiciera `certbot renew` sería
# peor que no tener cron: saldría con éxito sin haber renovado nada, y el
# certificado caducaría a los 90 días sin un solo aviso.
set -euo pipefail

cd "$(dirname "$0")/../.."

DOMINIO="${1:-}"
if [ -z "$DOMINIO" ]; then
    echo "Uso: $0 <DOMINIO>   (p. ej. torneos.tuclub.mx)" >&2
    exit 1
fi

# 1. Renovar.
#
# Se monta /etc/letsencrypt ENTERO, no solo live/. Ahí dentro está renewal/, que
# es donde certbot guarda cómo renovar cada certificado (el dominio, el método,
# el webroot). Sin renewal/, `certbot renew` no encuentra nada que renovar y sale
# con código 0: parece que funcionó y no renovó nada.
#
# El webroot es el MISMO directorio del host que nginx sirve en
# /.well-known/acme-challenge/ (ver docker-compose.publico.yml). Si no coincidiera,
# el desafío se escribiría donde nginx no lo publica y la validación fallaría.
docker run --rm \
    -v "$PWD/infra/letsencrypt:/etc/letsencrypt" \
    -v "$PWD/infra/certbot-www:/var/www/certbot" \
    certbot/certbot renew --quiet

# 2. Copiar los certificados a donde los lee nginx.
#
# `cp -L` (dereferencia) es imprescindible: en live/<DOMINIO>/ certbot no deja
# ficheros, sino symlinks RELATIVOS a ../../archive/<DOMINIO>/. Copiarlos tal cual
# (o montar ese directorio en nginx) dejaría enlaces rotos, porque archive/ no
# existe del otro lado del montaje.
cp -L "infra/letsencrypt/live/$DOMINIO/fullchain.pem" infra/nginx/certs/fullchain.pem
cp -L "infra/letsencrypt/live/$DOMINIO/privkey.pem"   infra/nginx/certs/privkey.pem
chmod 600 infra/nginx/certs/privkey.pem

# 3. Reiniciar nginx: lee el certificado una sola vez, al arrancar. Sin esto
# seguiría sirviendo el viejo hasta el próximo reinicio.
docker compose -f docker-compose.publico.yml restart nginx

echo "Certificado de $DOMINIO al día y nginx recargado."
