#!/usr/bin/env bash
#
# CONFIGURACIÓN DEL FIREWALL — Fase 2 de infraestructura
# =====================================================
#
# Requisito del PI: "Aplicación y monitoreo de Firewall".
# Este script es la parte de APLICACIÓN. La de MONITOREO son `estado-firewall.sh`
# (que demuestra qué está activo y qué está bloqueando) y `fail2ban`
# (que lee los logs, detecta ataques y banea).
#
# Uso:
#   # En la EC2 PÚBLICA (la que tiene la Elastic IP):
#   sudo ADMIN_IP=203.0.113.7 ./infra/firewall/configurar-firewall.sh publica
#
#   # En la EC2 PRIVADA (sin IP pública):
#   sudo IP_PUBLICA_PRIVADA=10.0.1.10 ./infra/firewall/configurar-firewall.sh privada
#
# Es IDEMPOTENTE: se puede correr las veces que haga falta sin duplicar reglas.
#
#
# *** LA TRAMPA QUE ESTE SCRIPT EXISTE PARA EVITAR ***
#
# Docker NO publica los puertos a través de la cadena INPUT. Cuando el compose
# dice `ports: ["8001:8000"]`, Docker inserta:
#
#   1. una regla DNAT en la tabla `nat` (PREROUTING), que reescribe el destino
#      del paquete: 10.0.2.10:8001 -> 172.18.0.x:8000 (la IP del contenedor);
#   2. el paquete, ya con destino "otra máquina", deja de ser tráfico local y se
#      encamina por la cadena FORWARD, NO por INPUT.
#
# `ufw` filtra en INPUT. Por lo tanto:
#
#   ufw deny 8001      <-- NO BLOQUEA ABSOLUTAMENTE NADA
#
# El firewall parecería configurado (`ufw status` mostraría la regla, en verde)
# y sería puramente DECORATIVO: el puerto 8001 seguiría abierto a quien lo
# alcance por la red. Es exactamente el fallo que el requisito busca detectar.
#
# La forma correcta de filtrar puertos publicados por Docker es la cadena
# DOCKER-USER: Docker la consulta ANTES de sus propias reglas de FORWARD y
# nunca la borra ni la reescribe (existe precisamente para esto).
#
# Reparto de responsabilidades en este script:
#   - ufw          -> puertos del PROPIO HOST:      22, 80, 443   (pasan por INPUT)
#   - DOCKER-USER  -> puertos publicados por Docker: 8001, 8002, 5000, 5432 (pasan por FORWARD)
#
#
# *** LA SEGUNDA TRAMPA: el puerto que se ve en DOCKER-USER NO es el publicado ***
#
# Cuando el paquete llega a DOCKER-USER, el DNAT YA OCURRIÓ: su puerto de
# destino ya no es 8001, sino 8000 (el puerto del contenedor). Así que:
#
#   iptables -I DOCKER-USER -p tcp --dport 8001 -j DROP   <-- tampoco bloquea nada
#
# Y peor: api1 (8001:8000) y api2 (8002:8000) escuchan en el MISMO puerto de
# contenedor (8000), así que `--dport 8000` ni siquiera permite distinguirlas.
# La solución es preguntarle a conntrack por el destino ORIGINAL del paquete,
# antes del DNAT:
#
#   -m conntrack --ctorigdstport 8001
#
# Eso sí identifica el puerto publicado, que es el que la gente ataca.
#
#
# *** LA TERCERA TRAMPA: no romper el tráfico entre contenedores ***
#
# Por DOCKER-USER pasa TAMBIÉN el tráfico contenedor-a-contenedor de la red
# `torneos_privada` (api -> db en el 5432, panel -> api en el 8000). Una regla
# ciega tipo "DROP a todo lo que vaya al 5432" tumbaría la aplicación entera.
# Por eso todas las reglas de abajo llevan `-i $INTERFAZ`: solo se aplican al
# tráfico que ENTRA POR LA TARJETA DE RED DEL HOST (el que viene de fuera de la
# máquina). El tráfico entre contenedores entra por la interfaz del puente
# (`br-xxxx`) y no lo tocamos.
#
#
# *** POR QUÉ "RETURN" Y NO "ACCEPT" EN LAS REGLAS DE PERMISO ***
#
# Un ACCEPT termina el recorrido de la cadena FORWARD: el paquete se acepta y ya.
# Eso saltaría por encima de las reglas que fail2ban inserta en DOCKER-USER para
# banear IPs, y los baneos dejarían de aplicarse. Con RETURN, el paquete permitido
# vuelve a DOCKER-USER y sigue evaluándose contra el resto de reglas (las de
# fail2ban incluidas). Firewall y fail2ban se complementan, no se pisan.
#
set -euo pipefail

# --------------------------------------------------------------------------
# Argumentos y entorno
# --------------------------------------------------------------------------

ROL="${1:-}"

uso() {
  cat >&2 <<'FIN'
Uso: sudo [VARIABLES] ./infra/firewall/configurar-firewall.sh <publica|privada>

  publica   La EC2 con IP pública: nginx (80/443) y SSH de administración.
            Requiere ADMIN_IP=<tu IP pública de administración>

              sudo ADMIN_IP=203.0.113.7 ./infra/firewall/configurar-firewall.sh publica

  privada   La EC2 sin IP pública: API x2, panel y PostgreSQL.
            Requiere IP_PUBLICA_PRIVADA=<IP que la EC2 PÚBLICA tiene DENTRO de la VPC>

              sudo IP_PUBLICA_PRIVADA=10.0.1.10 ./infra/firewall/configurar-firewall.sh privada

Variables opcionales:
  INTERFAZ=eth0   Interfaz de red externa del host (por defecto se autodetecta).
FIN
}

if [[ -z "$ROL" ]]; then
  echo "ERROR: falta el rol del servidor." >&2
  echo >&2
  uso
  exit 2
fi

if [[ "$ROL" != "publica" && "$ROL" != "privada" ]]; then
  echo "ERROR: rol inválido: '$ROL'. Los valores válidos son 'publica' o 'privada'." >&2
  echo >&2
  uso
  exit 2
fi

# Valida que una variable contenga algo con pinta de IPv4 (con o sin máscara).
# No es una validación exhaustiva: es para cazar un dedazo antes de meter basura
# en una regla de iptables, no para sustituir a la cabeza de quien despliega.
validar_ip() {
  local nombre="$1" valor="$2"
  if [[ ! "$valor" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}(/[0-9]{1,2})?$ ]]; then
    echo "ERROR: $nombre='$valor' no parece una dirección IPv4 válida (ej. 10.0.1.10 o 10.0.1.0/24)." >&2
    exit 1
  fi
}

# Las variables obligatorias se comprueban ANTES que el resto (root, ufw...):
# que falte ADMIN_IP es un error de USO, y quien lo comete tiene que enterarse
# aunque haya olvidado el sudo. Si no, el script se quejaría del sudo, el usuario
# lo añadiría, y solo entonces descubriría que además le falta la variable.
case "$ROL" in
  publica)
    # SSH solo desde la IP de administración. Sin esta variable, la única
    # alternativa sería abrir el 22 a 0.0.0.0/0, que es exactamente el agujero
    # que este script existe para cerrar: se aborta en vez de aplicar algo
    # peligroso.
    if [[ -z "${ADMIN_IP:-}" ]]; then
      cat >&2 <<'FIN'
ERROR: falta la variable ADMIN_IP.

  Sin ella habría que abrir el puerto 22 (SSH) a TODO INTERNET, que es justo lo
  que este firewall existe para impedir. Se aborta sin tocar nada.

  ADMIN_IP es la IP pública DESDE LA QUE administras (la de tu casa/oficina).
  Averíguala con:

      curl -s https://ifconfig.me

  Y vuelve a correr:

      sudo ADMIN_IP=<esa_ip> ./infra/firewall/configurar-firewall.sh publica

  Si tu IP es dinámica, usa el rango de tu ISP (ej. 203.0.113.0/24) o, mejor,
  entra por AWS Systems Manager Session Manager y no abras el 22 en absoluto.
FIN
      exit 1
    fi
    validar_ip ADMIN_IP "$ADMIN_IP"
    ;;
  privada)
    # IP que la EC2 PÚBLICA tiene DENTRO de la VPC (no su Elastic IP): es la
    # dirección con la que nginx aparece ante esta máquina.
    if [[ -z "${IP_PUBLICA_PRIVADA:-}" ]]; then
      cat >&2 <<'FIN'
ERROR: falta la variable IP_PUBLICA_PRIVADA.

  Es la IP que la EC2 PÚBLICA tiene DENTRO de la VPC (la privada, del rango
  10.0.1.0/24 según docs/DESPLIEGUE.md), NO su Elastic IP. Es el único origen
  que puede hablar con esta máquina: nginx.

  Averíguala DENTRO de la EC2 pública con:

      ec2metadata --local-ipv4   # o: curl -s http://169.254.169.254/latest/meta-data/local-ipv4

  Y vuelve a correr:

      sudo IP_PUBLICA_PRIVADA=<esa_ip> ./infra/firewall/configurar-firewall.sh privada
FIN
      exit 1
    fi
    validar_ip IP_PUBLICA_PRIVADA "$IP_PUBLICA_PRIVADA"
    ;;
esac

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: hay que correrlo como root (modifica ufw e iptables). Usa: sudo $0 $ROL" >&2
  exit 1
fi

# Interfaz externa del host: por ella entra el tráfico que viene de FUERA de la
# máquina. Se usa para NO tocar el tráfico entre contenedores (tercera trampa).
INTERFAZ="${INTERFAZ:-$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')}"
if [[ -z "$INTERFAZ" ]]; then
  echo "ERROR: no se pudo autodetectar la interfaz de red externa." >&2
  echo "       Pásala a mano:  sudo INTERFAZ=eth0 $0 $ROL" >&2
  exit 1
fi

if ! command -v ufw >/dev/null 2>&1; then
  echo "ERROR: ufw no está instalado." >&2
  echo "       Ubuntu/Debian:  sudo apt-get install -y ufw" >&2
  exit 1
fi

if ! command -v iptables >/dev/null 2>&1; then
  echo "ERROR: iptables no está instalado." >&2
  echo "       Ubuntu/Debian:  sudo apt-get install -y iptables" >&2
  exit 1
fi

# --------------------------------------------------------------------------
# Reglas comunes (ufw) — filtran el tráfico dirigido AL PROPIO HOST (INPUT)
# --------------------------------------------------------------------------

echo "==> Configurando ufw (rol: $ROL, interfaz externa: $INTERFAZ)"

# Política por defecto: no entra nada que no se permita explícitamente; la
# máquina sí puede salir (docker pull, apt, NAT Gateway...).
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null

# Loopback. ufw ya lo permite en before.rules, pero lo dejamos explícito: si
# alguien toca esas reglas, la política de arriba dejaría la máquina sin
# 127.0.0.1 y medio sistema (incluidos healthchecks locales) se caería.
ufw allow in on lo >/dev/null

# LOGGING: sin logs no hay monitoreo posible, y el requisito pide monitorear.
# ufw escribe en /var/log/ufw.log lo que bloquea; de ahí sacan su información
# tanto `estado-firewall.sh` como fail2ban.
ufw logging on >/dev/null

# --------------------------------------------------------------------------
# Utilidades para la cadena DOCKER-USER
# --------------------------------------------------------------------------

# Nuestras reglas NO van sueltas en DOCKER-USER, sino en una cadena propia
# (TORNEOS-FW) a la que DOCKER-USER salta. Motivo: para ser idempotentes hay que
# poder borrar y reescribir NUESTRAS reglas; si estuvieran mezcladas en
# DOCKER-USER, un `iptables -F DOCKER-USER` se llevaría por delante también las
# reglas de baneo que fail2ban inserta ahí. Con una cadena propia, vaciamos la
# nuestra y las de fail2ban ni se enteran.
CADENA="TORNEOS-FW"

docker_user_existe() {
  iptables -n -L DOCKER-USER >/dev/null 2>&1
}

preparar_cadena() {
  # Crea la cadena si no existe (el `||true` la hace idempotente) y la vacía,
  # para poder reescribir nuestras reglas desde cero en cada ejecución.
  iptables -N "$CADENA" 2>/dev/null || true
  iptables -F "$CADENA"

  # Enganchamos DOCKER-USER -> TORNEOS-FW. Se INSERTA (-I), no se añade (-A):
  # DOCKER-USER termina con un `RETURN` que Docker pone al crearla, así que una
  # regla añadida al final NUNCA se evaluaría.
  # El `-C` evita duplicar el salto si ya está puesto (idempotencia).
  if ! iptables -C DOCKER-USER -j "$CADENA" 2>/dev/null; then
    iptables -I DOCKER-USER 1 -j "$CADENA"
  fi
}

# Permite un puerto PUBLICADO por Docker solo desde un origen concreto.
#   $1 = puerto publicado (el de fuera: 8001, no el 8000 del contenedor)
#   $2 = IP de origen permitida
# Se usa RETURN, no ACCEPT, para no saltarse los baneos de fail2ban (ver cabecera).
permitir_puerto_docker() {
  local puerto="$1" origen="$2"
  iptables -A "$CADENA" -i "$INTERFAZ" -p tcp -s "$origen" \
    -m conntrack --ctorigdstport "$puerto" -j RETURN
}

# Bloquea todo lo demás que venga de fuera hacia un puerto publicado por Docker.
# Va SIEMPRE después del permiso correspondiente.
#   $1 = puerto publicado
#   $2 = etiqueta corta para el log (aparece en el prefijo, en /var/log/kern.log)
#
# OJO con la longitud de la etiqueta: iptables trunca --log-prefix a 29
# caracteres SIN AVISAR. Con el prefijo "[FW-BLOQ <etiqueta>] ", la etiqueta más
# larga que usamos es "panel:5000" -> 21 caracteres en total. Si alguien añade
# una etiqueta más larga (p. ej. "postgres:5432"), el prefijo se cortaría a
# medias y `estado-firewall.sh` ya no sabría leerlo. Etiquetas cortas.
bloquear_puerto_docker() {
  local puerto="$1" etiqueta="$2"
  # Primero LOG (limitado, para no llenar el disco si alguien escanea a saco) y
  # luego DROP. Sin log, un puerto bloqueado no se puede "monitorear": no habría
  # ninguna prueba de que el firewall está haciendo su trabajo.
  iptables -A "$CADENA" -i "$INTERFAZ" -p tcp \
    -m conntrack --ctorigdstport "$puerto" \
    -m limit --limit 5/min --limit-burst 10 \
    -j LOG --log-prefix "[FW-BLOQ $etiqueta] " --log-level 4
  iptables -A "$CADENA" -i "$INTERFAZ" -p tcp \
    -m conntrack --ctorigdstport "$puerto" -j DROP
}

# Persistencia. Las reglas de iptables viven en memoria: un reinicio de la VM se
# las lleva. (Un reinicio de DOCKER no: DOCKER-USER es justo la cadena que Docker
# respeta.) Paquete necesario en Ubuntu/Debian:
#
#     sudo apt-get install -y iptables-persistent netfilter-persistent
#
# (durante la instalación pregunta si guardar las reglas actuales: da igual lo
# que se conteste, este script las guarda al terminar).
guardar_reglas() {
  if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save >/dev/null
    echo "    Reglas guardadas con netfilter-persistent (se restauran al arrancar)."
  elif [[ -d /etc/iptables ]]; then
    iptables-save > /etc/iptables/rules.v4
    echo "    Reglas guardadas en /etc/iptables/rules.v4."
  else
    echo "    AVISO: no está instalado 'iptables-persistent'. Las reglas de DOCKER-USER"
    echo "           se PERDERÁN al reiniciar la máquina. Instálalo con:"
    echo "               sudo apt-get install -y iptables-persistent netfilter-persistent"
    echo "           (o vuelve a correr este script tras cada reinicio: es idempotente)."
  fi
}

# --------------------------------------------------------------------------
# Rol: PÚBLICA
# --------------------------------------------------------------------------

configurar_publica() {
  # ADMIN_IP ya está validada arriba (es obligatoria para este rol).
  echo "==> Rol PÚBLICA"

  # 22/tcp: solo administración. Estos SÍ pasan por INPUT (sshd corre en el
  # host, no en un contenedor), así que ufw es la herramienta correcta.
  ufw allow from "$ADMIN_IP" to any port 22 proto tcp comment 'SSH admin' >/dev/null
  echo "    SSH (22/tcp) permitido solo desde $ADMIN_IP"

  # 80 y 443: abiertos a internet. Son el único punto de entrada del sistema.
  #
  # OJO: nginx corre en un CONTENEDOR y publica 80/443, así que su tráfico NO
  # pasa por INPUT y estas dos reglas de ufw son, en rigor, decorativas: el
  # puerto estaría abierto igualmente. Se dejan a propósito, porque documentan la
  # intención y porque protegen el caso de que algún día nginx corra en el host.
  # Lo que de verdad protege el 80/443 aquí es fail2ban, que sí inserta sus
  # baneos en DOCKER-USER (ver infra/fail2ban/jail.local).
  ufw allow 80/tcp comment 'HTTP -> redirige a HTTPS' >/dev/null
  ufw allow 443/tcp comment 'HTTPS' >/dev/null
  echo "    HTTP (80/tcp) y HTTPS (443/tcp) abiertos a internet"

  ufw --force enable >/dev/null
  echo "    ufw activado"

  # 8443: el panel de monitoreo (Uptime Kuma), servido por nginx en su propio
  # puerto. NO puede quedar abierto a internet: hasta que se crea el usuario
  # admin, Kuma sirve su pantalla de configuración inicial a QUIEN LA PIDA, así
  # que cualquiera podría adelantarse y apropiarse del panel.
  #
  # Como lo publica un CONTENEDOR, la regla tiene que ir en la cadena de Docker:
  # un `ufw deny 8443` no lo bloquearía (el tráfico no pasa por INPUT).
  if docker_user_existe; then
    preparar_cadena

    permitir_puerto_docker 8443 "$ADMIN_IP"
    bloquear_puerto_docker 8443 "kuma:8443"
    echo "    Monitoreo (8443/tcp) permitido solo desde $ADMIN_IP"

    echo "    Cadena DOCKER-USER -> $CADENA preparada (para los baneos de fail2ban)"
    guardar_reglas
  else
    echo "    AVISO: la cadena DOCKER-USER no existe todavía (¿Docker parado?)."
    echo "           Levanta Docker y vuelve a correr este script."
  fi
}

# --------------------------------------------------------------------------
# Rol: PRIVADA
# --------------------------------------------------------------------------

configurar_privada() {
  # IP_PUBLICA_PRIVADA ya está validada arriba (es obligatoria para este rol).
  echo "==> Rol PRIVADA"

  # SSH solo desde la EC2 pública, que hace de bastión (`ssh -J`). Esta máquina
  # no tiene IP pública, pero eso no es una excusa para dejar el 22 abierto a
  # toda la VPC: cualquier otra instancia comprometida podría intentarlo.
  ufw allow from "$IP_PUBLICA_PRIVADA" to any port 22 proto tcp comment 'SSH desde el bastion' >/dev/null
  echo "    SSH (22/tcp) permitido solo desde $IP_PUBLICA_PRIVADA (bastión)"

  ufw --force enable >/dev/null
  echo "    ufw activado"

  # Aquí está el corazón del asunto: 8001, 8002 y 5000 los PUBLICA DOCKER, así
  # que ufw no los ve. Se filtran en DOCKER-USER o no se filtran.
  if ! docker_user_existe; then
    echo >&2 "ERROR: la cadena DOCKER-USER no existe: Docker no está instalado o no está corriendo."
    echo >&2 "       Sin ella NO se pueden filtrar los puertos 8001/8002/5000, que Docker publica"
    echo >&2 "       saltándose ufw. Arranca Docker (sudo systemctl start docker) y repite."
    exit 1
  fi

  preparar_cadena

  # Permitido: solo nginx (la EC2 pública) hacia los puertos publicados.
  permitir_puerto_docker 8001 "$IP_PUBLICA_PRIVADA"   # réplica 1 de la API
  permitir_puerto_docker 8002 "$IP_PUBLICA_PRIVADA"   # réplica 2 de la API
  permitir_puerto_docker 5000 "$IP_PUBLICA_PRIVADA"   # panel Flask
  echo "    DOCKER-USER: 8001, 8002 y 5000 permitidos SOLO desde $IP_PUBLICA_PRIVADA"

  # Prohibido: cualquier otro origen hacia esos mismos puertos.
  bloquear_puerto_docker 8001 "api1:8001"
  bloquear_puerto_docker 8002 "api2:8002"
  bloquear_puerto_docker 5000 "panel:5000"   # la etiqueta más larga: 21 chars con el prefijo
  echo "    DOCKER-USER: bloqueado (y registrado) todo el resto de tráfico a 8001, 8002 y 5000"

  # PostgreSQL (5432) NO se publica en ningún compose: solo se alcanza por la red
  # interna de Docker. Esta regla es DEFENSA EN PROFUNDIDAD: si alguien algún día
  # añade `ports: ["5432:5432"]` "para depurar un momento" y se le olvida
  # quitarlo, la base de datos NO quedará expuesta. El `-i $INTERFAZ` hace que
  # esto no toque el tráfico api->db, que va por la red interna de Docker.
  bloquear_puerto_docker 5432 "pg:5432"
  echo "    DOCKER-USER: 5432 (PostgreSQL) bloqueado desde fuera por defensa en profundidad"

  guardar_reglas
}

# --------------------------------------------------------------------------
# Ejecución
# --------------------------------------------------------------------------

case "$ROL" in
  publica) configurar_publica ;;
  privada) configurar_privada ;;
esac

# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------

echo
echo "======================================================================"
echo " FIREWALL APLICADO — servidor: $ROL"
echo "======================================================================"
echo
echo "ufw (tráfico hacia el propio host, cadena INPUT):"
ufw status verbose | sed 's/^/    /'
echo
if docker_user_existe; then
  echo "DOCKER-USER (tráfico hacia los puertos que publica Docker, cadena FORWARD):"
  iptables -n -L DOCKER-USER --line-numbers | sed 's/^/    /'
  echo
  echo "$CADENA (nuestras reglas):"
  iptables -n -L "$CADENA" --line-numbers | sed 's/^/    /'
  echo
fi
echo "Siguientes pasos:"
echo "  1. Instalar fail2ban:   sudo ./infra/fail2ban/instalar-fail2ban.sh $ROL"
echo "  2. Ver el estado y qué está bloqueando:   sudo ./infra/firewall/estado-firewall.sh"
echo
