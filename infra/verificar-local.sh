#!/bin/bash
# Verifica en local la infraestructura de producción, simulando las dos VMs de
# AWS: el compose "publico" (nginx) y el "privado" (API x2, panel, Postgres),
# unidos por la red `torneos_privada` que hace de red privada de la VPC.
#
# Uso:  ./infra/verificar-local.sh
#
# Se usa -k en curl porque el certificado es autofirmado: eso es lo esperado
# mientras no haya dominio. El cifrado es real; lo que el navegador no puede
# verificar es la identidad.
set -u

ENV_FILE=".env.produccion.local"
PRIVADO="docker compose --env-file $ENV_FILE -f docker-compose.privado.yml"
PUBLICO="docker compose --env-file $ENV_FILE -f docker-compose.publico.yml"

fallos=0
ok()    { echo "  OK      $1"; }
fallo() { echo "  FALLO   $1"; fallos=$((fallos + 1)); }

echo "=== 1. HTTP redirige a HTTPS ==="
codigo=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
[ "$codigo" = "301" ] && ok "http -> 301" || fallo "http devolvió $codigo (esperado 301)"

echo "=== 2. HTTPS: el panel carga ==="
codigo=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/login)
[ "$codigo" = "200" ] && ok "https /login -> 200" || fallo "/login devolvió $codigo"

echo "=== 3. La API responde a través de nginx ==="
salud=$(curl -sk https://localhost/api/health)
echo "$salud" | grep -q '"api":"ok"' && ok "$salud" || fallo "la API no responde: $salud"

echo "=== 4. EXACTAMENTE una cabecera HSTS ==="
# Dos cabeceras HSTS harían que el navegador descarte la política ENTERA: el
# requisito de SSL parecería cumplido sin estarlo. nginx debe ser el único que
# la emita (proxy_hide_header descarta la que mandan la API y el panel).
n=$(curl -sk -D- -o /dev/null https://localhost/login | grep -ci "^strict-transport-security")
[ "$n" = "1" ] && ok "1 cabecera HSTS" || fallo "hay $n cabeceras HSTS (debe haber exactamente 1)"

echo "=== 5. El BALANCEADOR reparte entre las dos réplicas ==="
for _ in $(seq 1 8); do curl -sk -o /dev/null https://localhost/api/health; done
a1=$(docker logs torneos_prod_api1 2>&1 | grep -c 'GET /health')
a2=$(docker logs torneos_prod_api2 2>&1 | grep -c 'GET /health')
if [ "$a1" -gt 0 ] && [ "$a2" -gt 0 ]; then
    ok "reparte de verdad (api1=$a1, api2=$a2)"
else
    fallo "no reparte (api1=$a1, api2=$a2): una réplica no recibe tráfico"
fi

echo "=== 6. Tolerancia a fallos: se apaga CADA réplica, una por una ==="
# Se prueban las DOS, no solo api2. Apagando únicamente api2 no se detectaba que
# el panel apuntaba a `api1` a pelo: con api1 caída el panel moría aunque api2
# siguiera viva. Ahora las dos réplicas comparten el alias de red `api`, así que
# también se comprueba desde DENTRO del panel que sigue alcanzando a la API.
for replica in torneos_prod_api1 torneos_prod_api2; do
    docker stop "$replica" >/dev/null 2>&1

    # a) El sistema sigue en pie a través de nginx (el balanceador descarta la caída).
    codigo=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/api/health)
    [ "$codigo" = "200" ] && ok "la API responde con $replica caída" \
                          || fallo "la API cayó al apagar $replica ($codigo)"

    # b) El panel sigue alcanzando a la API por el alias compartido `api`.
    if docker exec torneos_prod_web python -c \
        "import urllib.request; urllib.request.urlopen('http://api:8000/health', timeout=5)" \
        >/dev/null 2>&1; then
        ok "el panel alcanza la API con $replica caída"
    else
        fallo "el panel NO alcanza la API con $replica caída (¿API_URL apunta a una réplica concreta?)"
    fi

    docker start "$replica" >/dev/null 2>&1
    # Que vuelva a estar sana antes de apagar la siguiente (si no, se apagarían las dos).
    until docker exec "$replica" python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" \
        >/dev/null 2>&1; do sleep 1; done
done

echo "=== 7. La auditoría registra la IP REAL del cliente ==="
curl -sk -o /dev/null -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"correo":"intruso@demo.com","password":"mala"}'
sleep 1
docker logs torneos_prod_api1 2>&1 | grep AUDIT | tail -1
docker logs torneos_prod_api2 2>&1 | grep AUDIT | tail -1

echo "=== 8. Un atacante NO puede falsificar su IP (regresión de seguridad) ==="
# Si nginx anexara X-Forwarded-For en vez de sobrescribirla, uvicorn tomaría este
# valor forjado como IP del cliente. Rotándolo en cada petición, el atacante
# anularía el rate limiting por completo y envenenaría la auditoría.
# Se verificó explotable de verdad antes de corregirlo: no es teórico.
curl -sk -o /dev/null -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-For: 9.9.9.9" \
    -d '{"correo":"falsificador@demo.com","password":"mala"}'
sleep 1
if docker logs torneos_prod_api1 2>&1 | grep AUDIT | grep -q "9.9.9.9" ||
   docker logs torneos_prod_api2 2>&1 | grep AUDIT | grep -q "9.9.9.9"; then
    fallo "la IP falsificada (9.9.9.9) llegó a la auditoría."
    echo "          nginx debe SOBRESCRIBIR X-Forwarded-For con \$remote_addr, no anexarla."
else
    ok "la IP falsificada fue descartada"
fi

echo "=== 9. Postgres NO es accesible desde el host ==="
if (exec 3<>/dev/tcp/localhost/5432) 2>/dev/null; then
    fallo "Postgres está expuesto en el host"
else
    ok "Postgres no es accesible desde fuera"
fi

echo "=== 10. La API NO corre como superusuario ==="
es_super=$($PRIVADO exec -T db psql -U "${DB_ADMIN_USER:-torneos_admin}" -d "${DB_NAME:-torneos}" \
    -tAc "SELECT rolsuper FROM pg_roles WHERE rolname = '${DB_APP_USER:-torneos_app}';" 2>/dev/null | tr -d '[:space:]')
[ "$es_super" = "f" ] && ok "el usuario de la API no es superusuario" \
                      || fallo "el usuario de la API es superusuario (rolsuper=$es_super)"

echo "=== 11. El usuario de la API NO puede alterar el esquema (DDL) ==="
salida=$($PRIVADO exec -T db psql -U "${DB_APP_USER:-torneos_app}" -d "${DB_NAME:-torneos}" \
    -c "CREATE TABLE intento_ddl (id int);" 2>&1 | head -1)
echo "$salida" | grep -qi "permission denied" && ok "DDL denegado: $salida" \
                                              || fallo "pudo hacer DDL: $salida"

echo
if [ "$fallos" -eq 0 ]; then
    echo "TODO CORRECTO: la infraestructura cumple lo que promete."
else
    echo "$fallos COMPROBACIÓN(ES) FALLIDA(S)."
fi
exit "$fallos"
