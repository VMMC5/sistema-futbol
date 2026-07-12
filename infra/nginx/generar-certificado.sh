#!/bin/bash
# Genera un certificado autofirmado para poder servir HTTPS sin dominio.
#
# El cifrado es real; lo que el navegador no puede verificar es la identidad, así
# que mostrará una advertencia. Es lo esperado hasta que haya dominio.
#
# Cuando exista el dominio, certbot escribirá fullchain.pem y privkey.pem en esta
# misma ruta y nginx no necesitará ningún cambio (ver la guía de despliegue).
set -e

DESTINO="$(dirname "$0")/certs"
mkdir -p "$DESTINO"

if [ -f "$DESTINO/fullchain.pem" ]; then
    echo "Ya existe un certificado en $DESTINO. No se toca."
    exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$DESTINO/privkey.pem" \
    -out "$DESTINO/fullchain.pem" \
    -subj "/C=MX/ST=Hidalgo/L=Pachuca/O=Sistema de Torneos/CN=${1:-localhost}"

chmod 600 "$DESTINO/privkey.pem"
echo "Certificado autofirmado generado en $DESTINO (CN=${1:-localhost})."
