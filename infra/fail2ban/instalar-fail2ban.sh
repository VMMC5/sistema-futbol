#!/usr/bin/env bash
#
# INSTALACIÓN DE FAIL2BAN — Fase 2 de infraestructura
# ===================================================
#
# fail2ban es lo que convierte "aplicar el firewall" en "aplicar Y MONITOREAR el
# firewall", que es lo que pide el requisito del PI: lee los logs de los
# servicios que están abiertos (SSH, nginx), detecta ataques y banea al atacante
# modificando el firewall en caliente.
#
# Uso:
#   sudo ./infra/fail2ban/instalar-fail2ban.sh publica
#   sudo ./infra/fail2ban/instalar-fail2ban.sh privada
#
# En la PÚBLICA activa además las jaulas de nginx (que solo tienen sentido ahí,
# porque es donde corre nginx). Es idempotente: se puede repetir.
#
set -euo pipefail

ROL="${1:-}"

if [[ "$ROL" != "publica" && "$ROL" != "privada" ]]; then
  echo "ERROR: hay que decir en qué servidor estamos." >&2
  echo "Uso: sudo $0 <publica|privada>" >&2
  exit 2
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: hay que correrlo como root. Usa: sudo $0 $ROL" >&2
  exit 1
fi

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Directorio del host donde nginx (contenedor) deja sus logs. Tiene que coincidir
# con el bind mount de docker-compose.publico.yml:
#     - /var/log/nginx-torneos:/var/log/nginx
LOGS_NGINX="/var/log/nginx-torneos"

if ! command -v fail2ban-client >/dev/null 2>&1; then
  echo "==> Instalando fail2ban"
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    # python3-systemd: lo necesita el backend systemd de la jaula [sshd].
    apt-get install -y fail2ban python3-systemd
  else
    echo "ERROR: no hay apt-get. Instala fail2ban con el gestor de paquetes de tu distro." >&2
    exit 1
  fi
else
  echo "==> fail2ban ya está instalado"
fi

echo "==> Copiando la configuración"
install -m 0644 "$AQUI/jail.local" /etc/fail2ban/jail.local
install -d -m 0755 /etc/fail2ban/filter.d
install -m 0644 "$AQUI/filter.d/torneos-login.conf" /etc/fail2ban/filter.d/torneos-login.conf
echo "    /etc/fail2ban/jail.local"
echo "    /etc/fail2ban/filter.d/torneos-login.conf"

if [[ "$ROL" == "publica" ]]; then
  echo "==> Rol PÚBLICA: activando las jaulas de nginx"

  # El directorio tiene que existir ANTES de que arranque el contenedor de nginx
  # (si no, Docker lo crearía él y fail2ban podría arrancar antes de que haya
  # ningún fichero dentro, quejándose del logpath).
  install -d -m 0755 "$LOGS_NGINX"

  if [[ ! -f "$LOGS_NGINX/access.log" ]]; then
    echo "    AVISO: $LOGS_NGINX/access.log todavía no existe."
    echo "           Es lo esperable si nginx aún no ha arrancado con el bind mount"
    echo "           '- $LOGS_NGINX:/var/log/nginx' en docker-compose.publico.yml."
    echo "           fail2ban tolera un logpath ausente al arrancar y empieza a leerlo"
    echo "           en cuanto aparece, pero conviene comprobarlo después con:"
    echo "               sudo ./infra/firewall/estado-firewall.sh"
    # Se crea vacío para que la jaula arranque limpia desde el primer momento.
    : > "$LOGS_NGINX/access.log"
    : > "$LOGS_NGINX/error.log"
  fi

  # Las jaulas vienen con `enabled = false` en jail.local (para que en la EC2
  # privada, donde no hay nginx, no intenten leer un log que no existe).
  # Aquí sí las activamos, con un fichero aparte para no reescribir jail.local.
  cat > /etc/fail2ban/jail.d/nginx-torneos.local <<'FIN'
# Activa las jaulas de nginx. Solo en la EC2 PÚBLICA: es la única donde corre
# nginx. Lo escribe infra/fail2ban/instalar-fail2ban.sh; el resto de la
# configuración (logpath, banaction, DOCKER-USER...) está en jail.local.
[nginx-botsearch]
enabled = true

[torneos-login]
enabled = true
FIN
  echo "    /etc/fail2ban/jail.d/nginx-torneos.local (jaulas nginx-botsearch y torneos-login activadas)"
fi

echo "==> Comprobando la sintaxis de la configuración"
fail2ban-client -t

echo "==> Arrancando fail2ban"
systemctl enable fail2ban >/dev/null 2>&1 || true
systemctl restart fail2ban

echo
echo "======================================================================"
echo " FAIL2BAN INSTALADO — servidor: $ROL"
echo "======================================================================"
sleep 2
fail2ban-client status | sed 's/^/    /'
echo
echo "Para ver el firewall completo (reglas + baneos + quién intenta entrar):"
echo "    sudo ./infra/firewall/estado-firewall.sh"
echo
