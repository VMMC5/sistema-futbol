#!/usr/bin/env bash
#
# MONITOREO DEL FIREWALL — Fase 2 de infraestructura
# ==================================================
#
# Este script es EL ENTREGABLE de la segunda mitad del requisito del PI:
# "Aplicación y monitoreo de Firewall". Aplicar el firewall es `configurar-firewall.sh`;
# monitorearlo es poder DEMOSTRAR, en cualquier momento, que:
#
#   (a) está activo,
#   (b) los puertos que Docker publica están REALMENTE filtrados (y no solo
#       "denegados" en un ufw que nunca los ve — ver la cabecera de
#       configurar-firewall.sh),
#   (c) fail2ban está vigilando y a quién ha baneado,
#   (d) quién está intentando entrar y por dónde.
#
# Uso (no recibe argumentos):
#
#     sudo ./infra/firewall/estado-firewall.sh
#
# Degrada con elegancia: si falta ufw, fail2ban o iptables, lo dice en vez de
# reventar. Un servidor a medio configurar tiene que poder diagnosticarse.
#
set -uo pipefail
# Deliberadamente SIN `-e`: este script solo lee. Que un comando falle (porque
# falta un paquete o un log) es información que hay que MOSTRAR, no un motivo
# para abortar el informe entero a la mitad.

ROJO=$'\033[31m'; VERDE=$'\033[32m'; AMARILLO=$'\033[33m'; NEGRITA=$'\033[1m'; FIN=$'\033[0m'
# Sin colores si la salida no es una terminal (para poder redirigir a un fichero).
if [[ ! -t 1 ]]; then ROJO=""; VERDE=""; AMARILLO=""; NEGRITA=""; FIN=""; fi

titulo() {
  echo
  echo "${NEGRITA}======================================================================${FIN}"
  echo "${NEGRITA} $1${FIN}"
  echo "${NEGRITA}======================================================================${FIN}"
}

aviso()  { echo "${AMARILLO}  [!] $1${FIN}"; }
error()  { echo "${ROJO}  [x] $1${FIN}"; }
ok()     { echo "${VERDE}  [ok] $1${FIN}"; }

if [[ "${EUID}" -ne 0 ]]; then
  aviso "No estás como root: ufw, iptables y fail2ban no se pueden consultar sin privilegios."
  aviso "Vuelve a correrlo con:  sudo $0"
  exit 1
fi

echo "${NEGRITA}Estado del firewall — $(hostname) — $(date '+%Y-%m-%d %H:%M:%S')${FIN}"

# ----------------------------------------------------------------------------
# (a) ufw — el firewall del propio host (cadena INPUT): 22, 80, 443
# ----------------------------------------------------------------------------

titulo "1. ufw — tráfico dirigido al propio host (SSH, y en su caso 80/443)"

if ! command -v ufw >/dev/null 2>&1; then
  error "ufw NO está instalado."
  echo  "      Instálalo con: sudo apt-get install -y ufw"
  echo  "      y aplícalo con: sudo ./infra/firewall/configurar-firewall.sh <publica|privada>"
else
  estado_ufw="$(ufw status verbose 2>/dev/null)"
  if grep -q "Status: active" <<<"$estado_ufw"; then
    ok "ufw ACTIVO"
  else
    error "ufw está INACTIVO: el firewall del host no está aplicando nada."
  fi
  sed 's/^/      /' <<<"$estado_ufw"

  # Sin logging no hay monitoreo: fail2ban y el apartado (d) de este script
  # dependen de /var/log/ufw.log.
  if grep -qiE '^Logging: (on|low|medium|high|full)' <<<"$estado_ufw"; then
    ok "Logging activado (es lo que alimenta el conteo de bloqueos de abajo)."
  else
    error "Logging DESACTIVADO: sin logs no hay monitoreo. Actívalo con 'sudo ufw logging on'."
  fi
fi

# ----------------------------------------------------------------------------
# (b) DOCKER-USER — la única cadena que filtra los puertos publicados por Docker
# ----------------------------------------------------------------------------

titulo "2. DOCKER-USER — tráfico hacia los puertos que publica Docker (8001, 8002, 5000)"

echo "  Recordatorio: Docker publica sus puertos vía DNAT + FORWARD, NO vía INPUT."
echo "  ufw filtra en INPUT, así que un 'ufw deny 8001' NO bloquearía nada. Lo que"
echo "  de verdad protege esos puertos es lo que aparezca aquí abajo."
echo

if ! command -v iptables >/dev/null 2>&1; then
  error "iptables NO está instalado: no se puede comprobar el filtrado de los puertos de Docker."
elif ! iptables -n -L DOCKER-USER >/dev/null 2>&1; then
  aviso "La cadena DOCKER-USER no existe (Docker no está instalado o no ha arrancado nunca)."
  aviso "Mientras no exista, no hay puertos publicados... pero tampoco filtro alguno."
else
  echo "  ${NEGRITA}Cadena DOCKER-USER:${FIN}"
  iptables -n -L DOCKER-USER --line-numbers | sed 's/^/      /'
  echo

  if iptables -n -L TORNEOS-FW >/dev/null 2>&1; then
    echo "  ${NEGRITA}Cadena TORNEOS-FW (las reglas que aplica configurar-firewall.sh):${FIN}"
    iptables -n -L TORNEOS-FW --line-numbers -v | sed 's/^/      /'
    echo
    # Las columnas pkts/bytes de -v son la PRUEBA de que el firewall trabaja:
    # si un DROP tiene paquetes contados, es que ha bloqueado tráfico real.
    bloqueados="$(iptables -n -L TORNEOS-FW -v -x 2>/dev/null | awk '$3=="DROP" {suma+=$1} END {print suma+0}')"
    if [[ "$bloqueados" -gt 0 ]]; then
      ok "El firewall de Docker ha DESCARTADO $bloqueados paquetes (contador de las reglas DROP)."
    else
      echo "      Aún no ha descartado ningún paquete (contadores a 0). Normal en un servidor recién levantado."
    fi
  else
    error "La cadena TORNEOS-FW NO existe: los puertos 8001/8002/5000 NO están filtrados."
    echo  "      Aplícala con: sudo IP_PUBLICA_PRIVADA=<ip> ./infra/firewall/configurar-firewall.sh privada"
  fi
fi

# ----------------------------------------------------------------------------
# (c) fail2ban — el que convierte "aplicar" en "aplicar Y MONITOREAR"
# ----------------------------------------------------------------------------

titulo "3. fail2ban — jaulas activas e IPs baneadas"

if ! command -v fail2ban-client >/dev/null 2>&1; then
  error "fail2ban NO está instalado: el firewall está aplicado, pero NO monitoreado."
  echo  "      Instálalo y configúralo con: sudo ./infra/fail2ban/instalar-fail2ban.sh <publica|privada>"
elif ! fail2ban-client ping >/dev/null 2>&1; then
  error "fail2ban está instalado pero el servicio NO responde (¿parado?)."
  echo  "      Arráncalo con: sudo systemctl start fail2ban && sudo systemctl enable fail2ban"
else
  ok "fail2ban ACTIVO"
  jaulas="$(fail2ban-client status 2>/dev/null | sed -n 's/.*Jail list:[[:space:]]*//p' | tr -d ' ')"
  if [[ -z "$jaulas" ]]; then
    aviso "No hay ninguna jaula activa: fail2ban corre, pero no vigila nada."
  else
    total_baneadas=0
    IFS=',' read -ra lista <<<"$jaulas"
    for jaula in "${lista[@]}"; do
      [[ -z "$jaula" ]] && continue
      detalle="$(fail2ban-client status "$jaula" 2>/dev/null)"
      fallos_total="$(sed -n 's/.*Total failed:[[:space:]]*//p'  <<<"$detalle" | tr -d ' ')"
      baneos_total="$(sed -n 's/.*Total banned:[[:space:]]*//p'  <<<"$detalle" | tr -d ' ')"
      baneadas_ahora="$(sed -n 's/.*Currently banned:[[:space:]]*//p' <<<"$detalle" | tr -d ' ')"
      ips="$(sed -n 's/.*Banned IP list:[[:space:]]*//p' <<<"$detalle")"
      echo
      echo "  ${NEGRITA}Jaula: $jaula${FIN}"
      echo "      Intentos fallidos detectados : ${fallos_total:-0}"
      echo "      Baneos aplicados (histórico) : ${baneos_total:-0}"
      echo "      IPs baneadas ahora mismo     : ${baneadas_ahora:-0}"
      if [[ -n "${ips// /}" ]]; then
        echo "      -> ${ROJO}${ips}${FIN}"
      fi
      total_baneadas=$(( total_baneadas + ${baneadas_ahora:-0} ))
    done
    echo
    if [[ "$total_baneadas" -gt 0 ]]; then
      ok "$total_baneadas IP(s) baneadas en este momento: el monitoreo está funcionando."
    else
      echo "      Ninguna IP baneada ahora mismo."
    fi
  fi
fi

# ----------------------------------------------------------------------------
# (d) ¿Quién está intentando entrar? — los bloqueos que ha registrado el firewall
# ----------------------------------------------------------------------------

titulo "4. Últimos bloqueos registrados (quién intenta entrar y por dónde)"

LOG_UFW="/var/log/ufw.log"

# En algunos sistemas rsyslog no separa ufw.log y todo cae en kern.log/syslog.
if [[ ! -r "$LOG_UFW" ]]; then
  for alternativa in /var/log/kern.log /var/log/syslog /var/log/messages; do
    if [[ -r "$alternativa" ]]; then LOG_UFW="$alternativa"; break; fi
  done
fi

if [[ ! -r "$LOG_UFW" ]]; then
  aviso "No se encuentra ningún log del firewall (/var/log/ufw.log ni alternativos)."
  aviso "Comprueba que 'ufw logging' está en 'on' y que rsyslog corre."
else
  echo "  Fuente: $LOG_UFW"
  echo

  # Se cuentan tanto los bloqueos de ufw (INPUT: [UFW BLOCK]) como los de nuestra
  # cadena de Docker (FORWARD: [FW-BLOQ api1:8001], etc.), que es donde caen los
  # intentos contra 8001/8002/5000/5432.
  bloqueos="$(grep -E '\[UFW BLOCK\]|\[FW-BLOQ ' "$LOG_UFW" 2>/dev/null)"

  if [[ -z "$bloqueos" ]]; then
    echo "      Ningún bloqueo registrado todavía."
    echo "      (En un servidor recién expuesto a internet, esto se llena solo en minutos.)"
  else
    total="$(wc -l <<<"$bloqueos")"
    ok "$total bloqueos registrados en total."

    echo
    echo "  ${NEGRITA}Top 10 IPs de origen bloqueadas:${FIN}"
    printf '      %-8s %s\n' "INTENTOS" "IP DE ORIGEN"
    grep -oE 'SRC=[0-9.]+' <<<"$bloqueos" | cut -d= -f2 \
      | sort | uniq -c | sort -rn | head -10 \
      | awk '{printf "      %-8s %s\n", $1, $2}'

    echo
    echo "  ${NEGRITA}Top 10 puertos de destino atacados:${FIN}"
    echo "      (En las líneas de la cadena TORNEOS-FW, el DPT= del kernel es el puerto"
    echo "       del CONTENEDOR —el DNAT ya ocurrió—, no el publicado. El puerto publicado"
    echo "       que se atacó va en la etiqueta [FW-BLOQ ...] del apartado siguiente.)"
    printf '      %-8s %s\n' "INTENTOS" "PUERTO"
    grep -oE 'DPT=[0-9]+' <<<"$bloqueos" | cut -d= -f2 \
      | sort | uniq -c | sort -rn | head -10 \
      | awk '{printf "      %-8s %s\n", $1, $2}'

    servicios="$(grep -oE '\[FW-BLOQ [^]]+\]' <<<"$bloqueos" | sed 's/\[FW-BLOQ //; s/\]//')"
    if [[ -n "$servicios" ]]; then
      echo
      echo "  ${NEGRITA}Servicios de Docker contra los que se ha intentado entrar:${FIN}"
      printf '      %-8s %s\n' "INTENTOS" "SERVICIO:PUERTO PUBLICADO"
      sort <<<"$servicios" | uniq -c | sort -rn \
        | awk '{printf "      %-8s %s\n", $1, $2}'
    fi

    echo
    echo "  ${NEGRITA}Los 10 bloqueos más recientes:${FIN}"
    tail -10 <<<"$bloqueos" | sed 's/^/      /'
  fi
fi

echo
echo "${NEGRITA}Fin del informe.${FIN}"
echo
