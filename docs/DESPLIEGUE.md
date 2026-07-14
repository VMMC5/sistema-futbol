# Despliegue en AWS

Arquitectura de dos servidores, como exigen los Requerimientos Mínimos del PI:
uno de acceso público y otro privado.

```
Internet ──:443──> EC2 PÚBLICA (nginx: SSL + balanceador + Uptime Kuma en :8443)
                        │ red privada de la VPC
                        ▼
                   EC2 PRIVADA (API x2 + panel + PostgreSQL)
                   sin IP pública: inalcanzable desde internet
```

Cada VM lleva además su propio firewall dentro (`ufw` + `DOCKER-USER`) y
`fail2ban` vigilando los logs. Eso es la Fase 2, y está en las secciones 8, 9 y 10.

## 1. Red (VPC)

| Recurso | Valor |
|---|---|
| VPC | `10.0.0.0/16` |
| Subred pública | `10.0.1.0/24` — con Internet Gateway |
| Subred privada | `10.0.2.0/24` — sin Internet Gateway |
| NAT Gateway | En la subred pública. Deja que la EC2 privada **salga** a internet (para `docker pull`), pero impide que la alcancen desde fuera. |

## 2. Instancias

| | EC2 pública | EC2 privada |
|---|---|---|
| AMI | **Ubuntu Server 22.04 LTS** (o 24.04 LTS) | **Ubuntu Server 22.04 LTS** (o 24.04 LTS) |
| Usuario por defecto | `ubuntu` | `ubuntu` |
| Subred | pública | privada |
| IP pública | sí (Elastic IP) | **no** |
| IP privada sugerida | `10.0.1.10` (fija, dentro de la subred pública) | `10.0.2.10` (fija, dentro de la subred privada) |
| Tipo sugerido | t3.small | t3.medium |
| Software | Docker + Docker Compose | Docker + Docker Compose |

**Por qué Ubuntu y no Amazon Linux:** toda la Fase 2 (firewall y monitoreo) se
apoya en `ufw`, `fail2ban` e `iptables-persistent`, que se instalan con
`apt-get` y vienen en los repositorios de Ubuntu. Amazon Linux no trae `ufw`
(usa `firewalld`) ni `apt-get`, así que los scripts de `infra/firewall/` y
`infra/fail2ban/` no correrían allí.

Paquetes que hay que instalar en **las dos** VMs, además de Docker:

```bash
sudo apt-get update
sudo apt-get install -y ufw iptables-persistent netfilter-persistent
```

`iptables-persistent` pregunta durante la instalación si quiere guardar las
reglas actuales: da igual lo que se conteste, `configurar-firewall.sh` las
guarda él al terminar. Sin ese paquete, las reglas de `DOCKER-USER` se pierden
al reiniciar la máquina.

## 3. Security Groups (el firewall de AWS)

Los Security Groups son la **primera** capa: filtran en la red de AWS, antes de
que el paquete llegue siquiera a la VM. La segunda capa (`ufw` + `DOCKER-USER`,
sección 8) va dentro de la máquina. Las dos hacen falta: si un día alguien
relaja un Security Group "un momento para probar", el firewall de dentro sigue
protegiendo. Es defensa en profundidad.

**`sg-publica`** — entrada:

| Puerto | Origen | Motivo |
|---|---|---|
| 443 | `0.0.0.0/0` | HTTPS |
| 80 | `0.0.0.0/0` | Redirección a HTTPS y desafío de certbot |
| 8443 | **solo tu IP** | Panel de monitoreo (Uptime Kuma). Ver sección 10: **nunca** a `0.0.0.0/0`. |
| 22 | **solo tu IP** | SSH de administración |

**`sg-privada`** — entrada:

| Puerto | Origen | Motivo |
|---|---|---|
| 8001, 8002 | `sg-publica` | Las réplicas de la API, solo desde nginx |
| 5000 | `sg-publica` | El panel, solo desde nginx |
| 22 | `sg-publica` | SSH saltando desde la pública (bastión) |

**Nunca** se abre el 5432: Postgres solo se alcanza dentro de la propia EC2
privada.

## 4. Antes de tocar AWS: probar todo en local

El repositorio trae tres scripts en `infra/` que levantan **los mismos dos
compose de producción** (`docker-compose.publico.yml` y
`docker-compose.privado.yml`) en tu máquina local, simulando las dos EC2 con
una red Docker (`torneos_privada`) en vez de la red privada de la VPC. Sirven
para validar la arquitectura completa —migraciones efímeras, balanceo,
HSTS, IP real en la auditoría, usuario de BD sin privilegios de DDL, Uptime
Kuma, logs de nginx para fail2ban— **antes** de gastar tiempo depurando esto ya
en AWS:

```bash
./infra/levantar-local.sh      # levanta privado + público, corre migraciones, reinicia nginx
./infra/verificar-local.sh     # 15 comprobaciones automáticas (SSL, balanceador, seguridad, monitoreo...)
./infra/restaurar-desarrollo.sh   # vuelve al entorno de desarrollo de siempre
```

`verificar-local.sh` corre **15 comprobaciones**. Las 11 primeras son las de la
Fase 1 (redirección a HTTPS, HSTS única, balanceo real, tolerancia a la caída de
cada réplica, IP no falsificable, Postgres no expuesto, la API sin superusuario
ni DDL). Las cuatro últimas son de la Fase 2:

| # | Comprueba |
|---|---|
| 12 | Los **6 contenedores** (`db`, `api1`, `api2`, `web`, `nginx`, `kuma`) reportan `healthy` |
| 13 | **Uptime Kuma sirve su panel en el 8443** (y no en el sitio público) |
| 14 | **Kuma NO contamina las rutas del sitio público**: `https://localhost/dashboard` cae en el panel Flask (404), no en Kuma |
| 15 | **nginx deja logs legibles para fail2ban** en `/var/log/nginx-torneos/access.log` (si no, las jaulas de nginx no vigilarían nada) |

Cualquier fallo que reporte `verificar-local.sh` hay que resolverlo aquí, en
local, antes de desplegar en AWS.

`levantar-local.sh` no toca tu `.env`: genera `.env.produccion.local` aparte
(con contraseñas de prueba) y lo borra `restaurar-desarrollo.sh` al terminar.

**Tu base de datos de desarrollo no corre peligro.** Los dos compose de
producción declaran `name: torneos-prod`, así que Docker Compose los trata como
un proyecto aparte del de desarrollo (que toma el nombre del directorio,
`sistema-futbol`): volúmenes distintos (`torneos-prod_pgdata` frente a
`sistema-futbol_pgdata`) y contenedores distintos (`torneos_prod_db` frente a
`torneos_db`). La prueba levanta su propia base desde cero —que es lo que hace
falta para que corra el script de init de Postgres y se creen los dos roles— y
`restaurar-desarrollo.sh` borra solo esa. El stack de desarrollo únicamente se
**para** mientras dura la prueba, para liberar los puertos; sus datos siguen ahí
cuando lo vuelves a levantar.

## 5. Desplegar el servidor privado

```bash
ssh -J ubuntu@<IP_PUBLICA> ubuntu@10.0.2.10
git clone <REPO_GIT> && cd sistema-futbol
cp .env.example .env      # rellenar con los valores REALES
```

- `<IP_PUBLICA>`: la Elastic IP de la EC2 pública (el salto SSH pasa por ella,
  porque la privada no tiene IP pública).
- `<REPO_GIT>`: la URL de tu repositorio (p. ej. `git@github.com:tu-org/sistema-futbol.git`).

En `.env` hay que definir los dos usuarios de base de datos y el secreto de
firma:

```dotenv
DB_ADMIN_USER=torneos_admin
DB_ADMIN_PASSWORD=<generar: openssl rand -base64 24>
DB_APP_USER=torneos_app
DB_APP_PASSWORD=<generar: openssl rand -base64 24>
SECRET_KEY=<generar: openssl rand -hex 32>
```

`DB_NAME` ya viene con el valor por defecto (`torneos`) en `.env.example`; no
hace falta tocarlo salvo que quieras otro nombre.

Que las `DB_ADMIN_*` estén en el `.env` **no** significa que acaben en todos los
contenedores: ningún servicio de `docker-compose.privado.yml` usa `env_file`, que
volcaría el fichero entero en el entorno de cada uno. Cada servicio enumera las
variables que necesita, y las `DB_ADMIN_*` solo se las pasan `db` y `migraciones`.
Los contenedores de la API y el panel no las ven ni existiendo en el fichero:

```bash
docker compose -f docker-compose.privado.yml config | grep -A20 '^  api1:' | grep DB_ADMIN   # sin resultados
```

Las réplicas deben publicar sus puertos en la interfaz privada para que nginx
las alcance desde la otra EC2. Crear `docker-compose.privado.aws.yml`:

```yaml
services:
  api1:
    ports: ["8001:8000"]
  api2:
    ports: ["8002:8000"]
  web:
    ports: ["5000:5000"]
```

Y levantar:

```bash
docker network create torneos_privada
docker compose -f docker-compose.privado.yml -f docker-compose.privado.aws.yml up -d --build
```

> Publicar esos puertos con Docker es exactamente lo que obliga a la sección 8 a
> existir: Docker los abre saltándose `ufw`. Aplica el firewall de la sección 8
> **inmediatamente después** de este `up -d`.

### Migraciones: contenedor efímero, no `exec`

Las migraciones **no** se corren con `exec api1 alembic upgrade head`. Los
contenedores de la API son de larga duración y están expuestos a través de
nginx; por eso no reciben las credenciales de administrador de la base (si
alguien comprometiera la API, en su entorno no habría credenciales capaces de
alterar el esquema). Esas credenciales solo las recibe un servicio aparte,
`migraciones`, pensado para correr una vez y morir, con un `profile` que evita
que arranque con `up`:

```bash
docker compose -f docker-compose.privado.yml --profile migraciones run --rm migraciones
```

Usar `exec api1 alembic upgrade head` en este compose da
`permission denied for schema public`, porque `api1` se conecta con el usuario
limitado (`DB_APP_USER`), que no tiene permisos de DDL.

**No correr el seed**: `APP_ENV=production` hace que aborte, y así debe ser. El
primer superadmin se crea a mano.

### Documentos subidos: un volumen compartido por las dos réplicas

Los PDF que suben los aspirantes se guardan en disco (`UPLOAD_DIR=/datos/uploads`)
y luego los sirve la propia API. Con **dos** réplicas eso obliga a un volumen
compartido (`uploads`, montado en `api1` y `api2`): sin él, un documento subido a
`api1` daría 404 la mitad de las veces —cuando el balanceador enrutara al admin
a `api2`— y además se perdería en cada `up --build`. Si algún día hace falta una
tercera réplica **en otra máquina**, este volumen local deja de servir y hay que
mover los documentos a S3 o a EFS.

## 6. Desplegar el servidor público

```bash
ssh ubuntu@<IP_PUBLICA>
git clone <REPO_GIT> && cd sistema-futbol
```

Apuntar nginx a la EC2 privada, en `.env`:

```dotenv
API_1=10.0.2.10:8001
API_2=10.0.2.10:8002
WEB_1=10.0.2.10:5000
```

`KUMA_1` no hace falta tocarlo: Uptime Kuma vive en este mismo compose, así que
su valor por defecto (`kuma:3001`, el nombre del contenedor) vale igual en local
que en AWS.

Antes de levantar nginx, crear el directorio donde dejará sus logs (el que luego
vigila fail2ban; ver sección 9). Lo crea también
`infra/fail2ban/instalar-fail2ban.sh publica`, pero conviene que exista **antes**
de que arranque el contenedor:

```bash
sudo install -d -m 0755 /var/log/nginx-torneos
```

Generar el certificado y levantar:

```bash
./infra/nginx/generar-certificado.sh <IP_PUBLICA_O_DOMINIO>
docker network create torneos_privada
docker compose -f docker-compose.publico.yml up -d
```

Esto levanta **dos** contenedores: `nginx` (80, 443 y 8443) y `kuma` (el panel de
monitoreo, sin puerto propio: solo se llega a él por nginx, ver sección 10).

## 7. Reiniciar nginx tras recrear los backends

nginx resuelve las direcciones de los upstreams (`API_1`, `API_2`, `WEB_1`)
**una sola vez, al arrancar**, y las cachea. Si en algún momento recreas los
contenedores de la API en la EC2 privada (`up -d --build` tras un `git pull`,
por ejemplo), y el nombre o la dirección que nginx tenía cacheada dejó de
apuntar a un contenedor vivo, las peticiones empiezan a devolver 502. La
solución es forzar a nginx a resolver de nuevo:

```bash
docker compose -f docker-compose.publico.yml restart nginx
```

**En AWS esto casi nunca hace falta**, porque los upstreams configurados en
`.env` son la **IP fija** de la EC2 privada (`10.0.2.10:8001`, etc.), no un
nombre de contenedor Docker: esa IP no cambia aunque los contenedores de la
API se recreen. Donde sí importa reiniciar nginx es al probar todo con
`infra/levantar-local.sh` en un solo host, donde los upstreams son nombres de
contenedor (`api1:8000`) resueltos por la DNS interna de Docker; por eso ese
script lo hace automáticamente después de levantar el servidor privado. En
AWS, reinicia nginx solo si cambiaste la IP privada de la EC2 o los puertos
publicados.

## 8. Firewall dentro de cada VM (Fase 2)

Los Security Groups (sección 3) filtran en la red de AWS. Esta sección añade la
**segunda capa, dentro de la máquina**, que es lo que el requisito del PI llama
"Aplicación de Firewall". Se aplica con un único script,
`infra/firewall/configurar-firewall.sh`, que hay que correr **con `sudo`** y
diciéndole el rol de la máquina: `publica` o `privada`.

**Corre el script DESPUÉS de levantar los compose**: necesita que Docker esté
arrancado, porque parte de las reglas van en la cadena `DOCKER-USER`, que crea
Docker. En el rol `privada` el script **aborta** si esa cadena no existe (sin
ella los puertos 8001/8002/5000 quedarían sin filtrar y el firewall sería una
mentira). El script es **idempotente**: se puede repetir las veces que haga
falta.

### 8.1 La trampa: `ufw deny 8001` NO bloquea nada

Es el corazón del asunto, y por eso este script existe.

Cuando el compose dice `ports: ["8001:8000"]`, Docker **no** abre el puerto por
la vía normal. Inserta una regla **DNAT** que reescribe el destino del paquete
(`10.0.2.10:8001` → `172.18.0.x:8000`, la IP del contenedor). A partir de ahí el
paquete ya va dirigido a "otra máquina", así que el kernel lo encamina por la
cadena **FORWARD**, no por **INPUT**.

Y `ufw` filtra en **INPUT**. Por lo tanto:

```
sudo ufw deny 8001      # <-- NO BLOQUEA ABSOLUTAMENTE NADA
```

`ufw status` mostraría la regla, en verde, con muy buen aspecto. El firewall
parecería configurado y sería **puramente decorativo**: el puerto 8001 seguiría
abierto a cualquiera que lo alcance por la red. Este es exactamente el fallo que
el requisito busca detectar.

La cadena que Docker **sí** respeta —la consulta antes que sus propias reglas y
nunca la borra— es **`DOCKER-USER`**. De ahí el reparto de responsabilidades del
script:

| Mecanismo | Filtra | Puertos |
|---|---|---|
| `ufw` (cadena INPUT) | Los puertos del **propio host** (procesos que corren en la VM, como `sshd`) | 22, 80, 443 |
| `DOCKER-USER` (cadena FORWARD) | Los puertos que **publica Docker** (los contenedores) | 8001, 8002, 5000, 5432, 8443 |

El script no escribe sus reglas sueltas en `DOCKER-USER`, sino en una cadena
propia, `TORNEOS-FW`, a la que `DOCKER-USER` salta. Así puede vaciarla y
reescribirla en cada ejecución (idempotencia) sin llevarse por delante las reglas
de baneo que fail2ban inserta también en `DOCKER-USER`.

### 8.2 EC2 pública

Requiere la variable **`ADMIN_IP`**: la IP pública **desde la que administras**
(la de tu casa u oficina). Averíguala desde tu máquina, no desde la EC2:

```bash
curl -s https://ifconfig.me
```

Y aplica el firewall dentro de la EC2 pública:

```bash
sudo ADMIN_IP=<TU_IP_PUBLICA> ./infra/firewall/configurar-firewall.sh publica
```

**Sin `ADMIN_IP` el script ABORTA sin tocar nada, a propósito.** No hay valor por
defecto: la única alternativa sería abrir el puerto 22 a `0.0.0.0/0`, que es
justo el agujero que este firewall existe para cerrar. Si tu IP es dinámica, usa
el rango de tu ISP (p. ej. `203.0.113.0/24`, que el script también acepta).

Lo que deja aplicado:

- `ufw`: política por defecto `deny incoming` / `allow outgoing`, loopback
  permitido y **logging activado** (sin logs no hay monitoreo, y el requisito
  pide monitorear).
- **22/tcp solo desde `ADMIN_IP`** (`sshd` corre en el host: aquí `ufw` sí es la
  herramienta correcta).
- **80 y 443 abiertos a internet**: son el único punto de entrada del sistema.
- **8443/tcp (Uptime Kuma) solo desde `ADMIN_IP`**, y en `DOCKER-USER`, porque lo
  publica un contenedor. Ver la sección 10 para el porqué.

### 8.3 EC2 privada

Requiere la variable **`IP_PUBLICA_PRIVADA`**: la IP que la EC2 **pública** tiene
**dentro de la VPC** (del rango `10.0.1.0/24`), no su Elastic IP. Es la dirección
con la que nginx aparece ante esta máquina, y el único origen que debe poder
hablar con ella. Averíguala **dentro de la EC2 pública**:

```bash
ec2metadata --local-ipv4
# o: curl -s http://169.254.169.254/latest/meta-data/local-ipv4
```

Y aplica el firewall dentro de la EC2 privada:

```bash
sudo IP_PUBLICA_PRIVADA=10.0.1.10 ./infra/firewall/configurar-firewall.sh privada
```

Lo que deja aplicado:

- `ufw`: **22/tcp solo desde la EC2 pública** (el bastión del `ssh -J`). Que esta
  máquina no tenga IP pública no es excusa para dejar el 22 abierto a toda la
  VPC: otra instancia comprometida podría intentarlo.
- `DOCKER-USER`: **8001, 8002 y 5000 permitidos SOLO desde `IP_PUBLICA_PRIVADA`**
  (nginx), y **bloqueados y registrados** para cualquier otro origen.
- `DOCKER-USER`: **5432 (PostgreSQL) bloqueado desde fuera**, por defensa en
  profundidad. Postgres no se publica en ningún compose; esta regla cubre el día
  en que alguien añada `ports: ["5432:5432"]` "para depurar un momento" y se le
  olvide quitarlo.

### 8.4 Detalles que conviene conocer

- **Variable opcional `INTERFAZ`**: el script autodetecta la tarjeta de red
  externa del host (la de la ruta por defecto). Todas las reglas de `DOCKER-USER`
  llevan `-i <INTERFAZ>` para tocar **solo** el tráfico que viene de fuera de la
  máquina; el tráfico entre contenedores (api → db, panel → api) entra por la
  interfaz del puente Docker y no se toca, así que la aplicación no se rompe. Si
  la autodetección falla, pásala a mano:
  `sudo INTERFAZ=eth0 ADMIN_IP=... ./infra/firewall/configurar-firewall.sh publica`.
- **Persistencia**: las reglas de `iptables` viven en memoria y un reinicio de la
  VM se las lleva. El script las guarda con `netfilter-persistent` al terminar,
  pero eso requiere el paquete **`iptables-persistent`** (sección 2). Si no está,
  el script avisa: `Las reglas de DOCKER-USER se PERDERÁN al reiniciar`. Instala
  el paquete o vuelve a correr el script tras cada reinicio.
- Un reinicio de **Docker** sí es seguro: `DOCKER-USER` es precisamente la cadena
  que Docker respeta y nunca reescribe.

## 9. Monitoreo del firewall: fail2ban (Fase 2)

El requisito del PI no dice "aplicar un firewall": dice **"Aplicación y monitoreo
de Firewall"**. La sección 8 es la aplicación —una foto fija: no aprende, no
reacciona—. Esta sección es el monitoreo.

### 9.1 fail2ban: lo que convierte "aplicar" en "monitorear"

`fail2ban` lee continuamente los logs de los servicios que **sí** están abiertos
(SSH, nginx), detecta patrones de ataque y **modifica el firewall en caliente**
para banear al atacante. Sin él, el 22, el 80 y el 443 están abiertos y alguien
puede probar contraseñas indefinidamente: el firewall no se entera de nada,
porque desde su punto de vista ese tráfico va a un puerto permitido y es
legítimo.

Jaulas configuradas (`infra/fail2ban/jail.local`):

| Jaula | Qué vigila | Umbral | Baneo |
|---|---|---|---|
| `sshd` | Fuerza bruta contra SSH (lee el journal de systemd) | 4 fallos / 10 min | 1 h |
| `nginx-botsearch` | Escáneres pidiendo rutas de otros sistemas (`/wp-login.php`, `/.env`, `/phpmyadmin`...). Nuestro sistema no tiene ninguna: quien las pide es un bot. | 3 fallos / 10 min | 24 h |
| `torneos-login` | Fuerza bruta contra **nuestro** login. Filtro propio (`infra/fail2ban/filter.d/torneos-login.conf`): cuenta `POST /api/auth/login` con 401 y `POST /login` con 200 (el panel Flask no devuelve 401 al fallar: repinta el formulario). | 5 fallos / 10 min | 2 h |

Los baneos **escalan**: quien reincide es baneado el doble de tiempo cada vez
(1 h, 2 h, 4 h...) hasta 1 semana. Un escáner automatizado acaba fuera durante
días sin intervención humana.

Las dos jaulas de nginx banean en `DOCKER-USER`
(`banaction = iptables-allports[chain=DOCKER-USER]`), no en INPUT: nginx corre en
un contenedor y un baneo en INPUT no bloquearía nada (misma trampa de la sección
8.1). La jaula de `sshd` sí usa INPUT, que es lo correcto: `sshd` corre en el
host.

### 9.2 AVISO: rellena `ignoreip` ANTES de instalar

En `infra/fail2ban/jail.local`, la línea `ignoreip` lista las redes que **nunca**
se banean:

```
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/16 172.16.0.0/12
```

**Añade ahí tu IP pública de administración antes de desplegar.** Si no lo haces
y te equivocas cuatro veces con la clave SSH, **te baneas a ti mismo** y te
quedas fuera de la máquina: para recuperarla hay que entrar por la consola serie
de AWS. Es el error más caro de esta fase y se evita editando una línea:

```
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/16 172.16.0.0/12 <TU_IP_PUBLICA>
```

(`10.0.0.0/16` ya está por un motivo parecido: si nginx se autobaneara al llamar
a la EC2 privada, caería el sistema entero.)

### 9.3 Instalación

En **cada** VM, con su rol:

```bash
# En la EC2 pública:
sudo ./infra/fail2ban/instalar-fail2ban.sh publica

# En la EC2 privada:
sudo ./infra/fail2ban/instalar-fail2ban.sh privada
```

El script instala `fail2ban` y `python3-systemd`, copia `jail.local` y el filtro
propio a `/etc/fail2ban/`, comprueba la sintaxis (`fail2ban-client -t`) y arranca
el servicio. En el rol `publica` **además** crea
`/etc/fail2ban/jail.d/nginx-torneos.local` para activar las jaulas de nginx (que
solo tienen sentido ahí: en la privada no hay nginx) y se asegura de que exista
`/var/log/nginx-torneos/`. Es idempotente.

### 9.4 Los logs de nginx: por qué el compose monta un directorio del host

fail2ban corre en el **host**, no en un contenedor, y necesita **leer** los logs
de nginx. La imagen oficial de nginx enlaza `/var/log/nginx/access.log` y
`error.log` a `/dev/stdout` y `/dev/stderr`: los logs solo salen por
`docker logs`, que fail2ban no sabe leer.

Por eso `docker-compose.publico.yml` monta un directorio del host encima:

```yaml
volumes:
  - /var/log/nginx-torneos:/var/log/nginx
```

Al montar encima, esos symlinks desaparecen y nginx escribe **ficheros de
verdad**, que quedan en el host: `/var/log/nginx-torneos/access.log` y
`error.log`. Ahí es donde apuntan los `logpath` de las jaulas.

> **Efecto colateral esperado**: `docker compose -f docker-compose.publico.yml logs nginx`
> **ya no muestra las peticiones**. Están en `/var/log/nginx-torneos/access.log`:
>
> ```bash
> sudo tail -f /var/log/nginx-torneos/access.log
> ```

### 9.5 El comando que DEMUESTRA que el firewall funciona

```bash
sudo ./infra/firewall/estado-firewall.sh
```

No recibe argumentos y solo lee (no modifica nada). Es el entregable de la parte
de **monitoreo** del requisito: en un vistazo demuestra que el firewall está
activo y qué está bloqueando. Imprime cuatro bloques:

1. **`ufw`**: si está `ACTIVO`, sus reglas, y si el logging está encendido (sin
   logging no hay monitoreo: es lo que alimenta el bloque 4).
2. **`DOCKER-USER` y `TORNEOS-FW`**: las reglas que filtran los puertos que
   publica Docker, **con los contadores de paquetes**. Un `DROP` con paquetes
   contados es la prueba de que el firewall ha bloqueado tráfico real, no de que
   "la regla está puesta".
3. **`fail2ban`**: las jaulas activas y, por cada una, intentos fallidos
   detectados, baneos aplicados y **las IPs baneadas ahora mismo**.
4. **Últimos bloqueos registrados**: de dónde vienen los intentos. Un conteo
   **por IP de origen** (top 10), por puerto de destino, por servicio de Docker
   atacado (leído de la etiqueta `[FW-BLOQ api1:8001]` que el firewall deja en el
   log) y las 10 líneas más recientes.

Si falta `ufw`, `iptables` o `fail2ban`, el script **lo dice y sigue** en vez de
reventar: un servidor a medio configurar tiene que poder diagnosticarse. Es el
comando que hay que enseñar para acreditar el requisito, y el primero que hay que
correr cuando algo deje de responder.

## 10. Monitoreo del sistema: Uptime Kuma (Fase 2)

Uptime Kuma hace ping continuamente a la API, al panel y al sitio público, guarda
el histórico y avisa cuando algo se cae. Corre en la **EC2 pública** a propósito:
si viviera en la privada y cayera la red entre ambas, el panel que debe avisarte
del corte sería inalcanzable.

### 10.1 Dónde vive: en su PROPIO puerto, el 8443

```
https://<IP_PUBLICA>:8443
```

No está en el sitio público (`https://<IP_PUBLICA>/monitor` **no existe**). El
contenedor `kuma` no publica ningún puerto: solo se llega a él a través de nginx,
que le dedica un bloque `server { listen 8443 ssl; ... }` con el mismo
certificado. Dos razones para el puerto aparte, las dos comprobadas:

- **Kuma 1.x no se puede servir desde un subpath.** Su HTML referencia los
  recursos anclados a la raíz (`/assets/...`, `/icon.svg`) y su router navega a
  `/dashboard`, no a `/monitor/dashboard`. Meterlo en el sitio principal obligaba
  a reservarle **~24 rutas de primer nivel**, que además **ganaban** sobre las del
  panel de administración: el día que el panel necesitara `/settings` o `/status`,
  dejaría de funcionar.
- **Kuma sirve su pantalla de configuración inicial a QUIEN LA PIDA** hasta que se
  crea el usuario administrador. Expuesto a internet, cualquiera podría
  adelantarse y **apropiarse del panel de monitoreo**.

Por eso el firewall (sección 8.2) abre el 8443 **solo desde `ADMIN_IP`**, y el
Security Group `sg-publica` también (sección 3). Nunca a `0.0.0.0/0`.

### 10.2 PRIMER PASO OBLIGATORIO tras desplegar

Nada más levantar el compose público, entra y **crea el usuario administrador de
Kuma inmediatamente**:

```
https://<IP_PUBLICA>:8443
```

- `<IP_PUBLICA>`: la Elastic IP de la EC2 pública.
- El navegador avisará del certificado autofirmado mientras no haya dominio: es
  lo esperado (el cifrado es real; lo que no puede verificar es la identidad).

No lo dejes para después. Aunque el firewall solo permita tu IP, ese formulario de
configuración inicial es una cuenta de administrador esperando a que alguien la
reclame.

### 10.3 Monitores que dar de alta

Una vez dentro, `Add New Monitor` para cada uno:

| Monitor | Tipo | URL / destino | Para qué |
|---|---|---|---|
| Sitio público (extremo a extremo) | HTTP(s) | `https://<IP_PUBLICA>/api/health` | Lo que ve un usuario real: TLS + nginx + balanceador + API + base de datos. La API responde `{"api":"ok","base_de_datos":"ok"}`, así que **también cubre Postgres**. Marca *Ignore TLS error* mientras el certificado sea autofirmado. |
| Réplica 1 de la API | HTTP(s) | `http://10.0.2.10:8001/health` | **Por separado**, para ver si se cae **una** réplica. Contra el balanceador no se notaría: el sistema seguiría en pie con la otra, y el balanceador estaría tapando una avería. |
| Réplica 2 de la API | HTTP(s) | `http://10.0.2.10:8002/health` | Igual que la anterior. |
| Panel de administración | HTTP(s) | `http://10.0.2.10:5000/login` | El panel Flask, directamente en la EC2 privada. |
| PostgreSQL | TCP Port | `10.0.2.10` : `5432` | Ver el aviso de abajo. |

Kuma alcanza los tres puertos privados porque corre **en la EC2 pública**, que es
justo el único origen que el firewall de la EC2 privada permite hacia 8001, 8002
y 5000 (sección 8.3). No hay que abrir nada más.

> **Aviso sobre el monitor de Postgres.** El 5432 **no se publica** en ningún
> compose y `DOCKER-USER` lo bloquea desde fuera (sección 8.3): un monitor TCP de
> Kuma contra `10.0.2.10:5432` daría **siempre caído**, y eso es lo correcto —es
> la prueba de que la base de datos no es alcanzable desde otra máquina—. Si
> quieres un monitor TCP de Postgres que sirva de algo, lánzalo **desde la propia
> EC2 privada** (donde sí se alcanza por la red interna de Docker), o quédate con
> el `healthcheck` de `db` y con `"base_de_datos":"ok"` de `/api/health`, que ya
> te dicen si Postgres está vivo.

Comprobar desde tu máquina, antes de configurar nada, que el 8443 responde:

```bash
curl -skI --max-time 5 https://<IP_PUBLICA>:8443/    # 200
```

Y desde **cualquier otra** IP, que **no** responde (debe dar timeout): eso es el
firewall haciendo su trabajo.

### 10.4 La capa de debajo: los healthchecks de Docker

Uptime Kuma vigila **desde fuera** y avisa. Debajo hay una capa que **actúa**:
todos los servicios declaran `healthcheck` en los compose, y con
`restart: unless-stopped` Docker reinicia lo que muera.

```bash
docker compose -f docker-compose.privado.yml ps    # db, api1, api2, web -> healthy
docker compose -f docker-compose.publico.yml  ps    # nginx, kuma        -> healthy
```

Los **6 contenedores** deben mostrar `(healthy)`. Es la comprobación 12 de
`verificar-local.sh`. Si Docker reinicia un contenedor y se recupera solo,
Kuma lo registrará como una caída breve en el histórico: ahí es donde se ve la
diferencia entre "no pasó nada" y "algo se está cayendo cada noche".

## 11. Certificado real (cuando haya dominio)

Mientras no hay dominio, el certificado es autofirmado: **cifra de verdad**, pero
el navegador avisa de que no puede verificar la identidad. Con un dominio
apuntando a la Elastic IP, se sustituye por uno real y gratuito de Let's Encrypt.

### Cómo encajan las piezas

Certbot y nginx son dos contenedores distintos que tienen que ponerse de acuerdo
en **dos** directorios del host. Si uno de los dos no cuadra, el procedimiento
falla, y a veces falla **en silencio**:

| Directorio del host | Lo escribe | Lo lee | Para qué |
|---|---|---|---|
| `infra/certbot-www/` | certbot | nginx (`location /.well-known/acme-challenge/`) | El desafío HTTP-01: Let's Encrypt tiene que poder descargar por HTTP el fichero que certbot deja aquí. |
| `infra/letsencrypt/` | certbot | certbot | Los certificados **y** `renewal/`, que es donde certbot apunta cómo renovar cada dominio. |
| `infra/nginx/certs/` | tú (`cp -L`) | nginx | El `fullchain.pem` y el `privkey.pem` que nginx sirve. |

Dos cosas que conviene tener claras, porque son las que rompen el 90 % de las
guías de internet:

- **Nunca uses un volumen nombrado (`-v certbot_www:...`) para el webroot.**
  Compose le pone el prefijo del proyecto (`torneos-prod_certbot_www`), así que un
  `docker run -v certbot_www:...` suelto crearía un volumen **distinto**: el
  desafío se escribiría donde nginx no lo sirve y la validación fallaría. Por eso
  el webroot es un bind mount a `./infra/certbot-www`, el mismo del lado de nginx.
- **Monta `/etc/letsencrypt` entero, no solo `live/`.** En `live/<DOMINIO>/`
  certbot no deja ficheros, sino **symlinks relativos** a `../../archive/`; si
  montas solo ese directorio, del otro lado quedan enlaces rotos. Y sin
  `renewal/`, `certbot renew` no encuentra qué renovar, **no renueva nada y sale
  con éxito**: el certificado caducaría a los 90 días sin un solo aviso.

### Emitir el certificado (una vez)

nginx tiene que estar **ya levantado** (sección 6, con el certificado
autofirmado): es quien sirve el desafío por el puerto 80.

```bash
# 1. Emitir. Certbot deja el desafío en el webroot que nginx publica.
sudo docker run --rm \
  -v "$PWD/infra/letsencrypt:/etc/letsencrypt" \
  -v "$PWD/infra/certbot-www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d <DOMINIO> --agree-tos -m <CORREO_ADMIN> --no-eff-email

# 2. Copiar a donde nginx los lee, DEFERENCIANDO los symlinks (cp -L).
sudo cp -L infra/letsencrypt/live/<DOMINIO>/fullchain.pem infra/nginx/certs/fullchain.pem
sudo cp -L infra/letsencrypt/live/<DOMINIO>/privkey.pem   infra/nginx/certs/privkey.pem
sudo chmod 600 infra/nginx/certs/privkey.pem

# 3. Reiniciar: nginx lee el certificado una sola vez, al arrancar.
docker compose -f docker-compose.publico.yml restart nginx
```

- `<DOMINIO>`: el dominio real apuntando a la Elastic IP (p. ej. `torneos.tuclub.mx`).
- `<CORREO_ADMIN>`: un correo tuyo, para los avisos de expiración de Let's Encrypt.
- `sudo` porque certbot corre como root y los ficheros que deja son suyos.

El `restart nginx` de aquí es imprescindible, y no es el mismo caso de la
sección 7: allí cambiaba la dirección de un backend; aquí cambia el contenido
del certificado. El mismo certificado lo sirve también el puerto 8443 (Uptime
Kuma), así que el aviso del navegador desaparece también allí.

Comprobar que quedó bien (ya sin `-k`: si el certificado es válido, `curl` lo
acepta sin protestar):

```bash
curl https://<DOMINIO>/api/health          # {"api":"ok","base_de_datos":"ok"}
```

### Renovar (automático)

Los certificados de Let's Encrypt duran **90 días**. La renovación repite los
mismos tres pasos —`certbot renew`, `cp -L`, `restart nginx`—, que es justo lo
que hace `infra/nginx/renovar-certificado.sh`:

```bash
sudo crontab -e
```

```cron
# Diario a las 3:00. Certbot solo renueva si quedan menos de 30 días; el resto
# de los días no hace nada y sale con éxito, así que correrlo a diario es seguro
# y deja 30 días de margen si un día falla.
0 3 * * * cd /home/ubuntu/sistema-futbol && ./infra/nginx/renovar-certificado.sh <DOMINIO> >> /var/log/certbot-renovacion.log 2>&1
```

Antes de fiarse del cron, conviene probar el script una vez a mano —debe terminar
con `Certificado de <DOMINIO> al día y nginx recargado.`— y ensayar la renovación
en seco, que valida el desafío de verdad sin gastar cuota de Let's Encrypt:

```bash
sudo docker run --rm \
  -v "$PWD/infra/letsencrypt:/etc/letsencrypt" \
  -v "$PWD/infra/certbot-www:/var/www/certbot" \
  certbot/certbot renew --dry-run
```

## 12. Comprobación del despliegue

### 12.1 Local, antes de tocar AWS

Antes de repetir estos pasos ya en AWS, corre la validación completa en tu
máquina con los scripts de la sección 4
(`infra/levantar-local.sh`, `infra/verificar-local.sh`,
`infra/restaurar-desarrollo.sh`). Las **15 comprobaciones** deben pasar. Detectar
ahí un fallo —una migración que no corre, un 502 de nginx, una cabecera HSTS
duplicada, Kuma comiéndose las rutas del panel, nginx sin dejar logs para
fail2ban— es mucho más rápido que depurarlo por SSH contra dos EC2.

### 12.2 Ya en AWS

El sistema, desde fuera:

```bash
curl -k https://<IP_PUBLICA>/api/health          # {"api":"ok","base_de_datos":"ok"}
curl -I http://<IP_PUBLICA>                       # 301 a https
curl -sk -D- -o /dev/null https://<IP_PUBLICA>/ | grep -ci strict-transport   # 1
```

Que **la privada no se alcanza desde fuera** (esto debe fallar):

```bash
curl --max-time 5 http://10.0.2.10:8001/health   # debe dar timeout
```

El **monitoreo**, desde tu IP de administración:

```bash
curl -skI --max-time 5 https://<IP_PUBLICA>:8443/   # 200 (Uptime Kuma)
```

Y el **firewall**, dentro de cada VM:

```bash
sudo ./infra/firewall/estado-firewall.sh
```

Debe mostrar `ufw ACTIVO`, la cadena `TORNEOS-FW` con sus reglas, `fail2ban
ACTIVO` con sus jaulas (`sshd`, y en la pública también `nginx-botsearch` y
`torneos-login`) y, al cabo de unas horas expuesto a internet, un buen puñado de
bloqueos registrados con sus IPs de origen.

---

## Resumen de la verificación

| Requisito del PI | Cómo se comprueba |
|---|---|
| Dos servidores (público/privado) | Los dos compose; la privada sin IP pública y con Postgres inalcanzable |
| Certificado SSL | HTTPS responde; HTTP redirige con 301 |
| Balanceador de carga | Ambas réplicas atienden peticiones; se apaga una y el sistema sigue en pie |
| **Firewall aplicado** | Security Groups (capa 1) + `ufw` y `DOCKER-USER` dentro de cada VM (capa 2), con `configurar-firewall.sh`. Los puertos de Docker se filtran donde de verdad se filtran, no en un `ufw` decorativo. |
| **Firewall monitoreado** | `estado-firewall.sh` (reglas activas, contadores de paquetes descartados, IPs baneadas, top de atacantes) + `fail2ban` baneando en caliente (`sshd`, `nginx-botsearch`, `torneos-login`) |
| **Monitoreo del sistema** | Uptime Kuma en `https://<IP_PUBLICA>:8443` (sitio público, las dos réplicas por separado, el panel) + `healthcheck` de Docker en los 6 contenedores |
| — (arreglo) HSTS | Exactamente una cabecera, no dos |
| — (arreglo) IP real | La auditoría registra la IP del cliente, no la de nginx |
| — (extra) Menor privilegio | La API no es superusuario, no puede hacer DDL, y las migraciones corren en un contenedor efímero aparte |

Las 15 comprobaciones de `./infra/verificar-local.sh` cubren todo esto de forma
automática antes de desplegar.
