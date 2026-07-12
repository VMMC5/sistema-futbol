# Despliegue en AWS

Arquitectura de dos servidores, como exigen los Requerimientos Mínimos del PI:
uno de acceso público y otro privado.

```
Internet ──:443──> EC2 PÚBLICA (nginx: SSL + balanceador)
                        │ red privada de la VPC
                        ▼
                   EC2 PRIVADA (API x2 + panel + PostgreSQL)
                   sin IP pública: inalcanzable desde internet
```

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
| Subred | pública | privada |
| IP pública | sí (Elastic IP) | **no** |
| IP privada sugerida | — | `10.0.2.10` (fija, dentro de la subred privada) |
| Tipo sugerido | t3.small | t3.medium |
| Software | Docker + Docker Compose | Docker + Docker Compose |

## 3. Security Groups (el firewall de AWS)

**`sg-publica`** — entrada:

| Puerto | Origen | Motivo |
|---|---|---|
| 443 | `0.0.0.0/0` | HTTPS |
| 80 | `0.0.0.0/0` | Redirección a HTTPS y desafío de certbot |
| 22 | **solo tu IP** | SSH de administración |

**`sg-privada`** — entrada:

| Puerto | Origen | Motivo |
|---|---|---|
| 8001, 8002 | `sg-publica` | Las réplicas de la API, solo desde nginx |
| 5000 | `sg-publica` | El panel, solo desde nginx |
| 22 | `sg-publica` | SSH saltando desde la pública (bastión) |

**Nunca** se abre el 5432: Postgres solo se alcanza dentro de la propia EC2 privada.

> La Fase 2 añade `ufw` dentro de cada VM como segunda capa, más `fail2ban` para
> monitorear el firewall.

## 4. Antes de tocar AWS: probar todo en local

El repositorio trae tres scripts en `infra/` que levantan **los mismos dos
compose de producción** (`docker-compose.publico.yml` y
`docker-compose.privado.yml`) en tu máquina local, simulando las dos EC2 con
una red Docker (`torneos_privada`) en vez de la red privada de la VPC. Sirven
para validar la arquitectura completa —migraciones efímeras, balanceo,
HSTS, IP real en la auditoría, usuario de BD sin privilegios de DDL— **antes**
de gastar tiempo depurando esto ya en AWS:

```bash
./infra/levantar-local.sh      # levanta privado + público, corre migraciones, reinicia nginx
./infra/verificar-local.sh     # 11 comprobaciones automáticas (SSL, balanceador, seguridad...)
./infra/restaurar-desarrollo.sh   # vuelve al entorno de desarrollo de siempre
```

`levantar-local.sh` no toca tu `.env`: genera `.env.produccion.local` aparte
(con contraseñas de prueba) y lo borra `restaurar-desarrollo.sh` al terminar.
Cualquier fallo que reporte `verificar-local.sh` hay que resolverlo aquí,
en local, antes de desplegar en AWS.

## 5. Desplegar el servidor privado

```bash
ssh -J ec2-user@<IP_PUBLICA> ec2-user@10.0.2.10
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

## 6. Desplegar el servidor público

```bash
ssh ec2-user@<IP_PUBLICA>
git clone <REPO_GIT> && cd sistema-futbol
```

Apuntar nginx a la EC2 privada, en `.env`:

```dotenv
API_1=10.0.2.10:8001
API_2=10.0.2.10:8002
WEB_1=10.0.2.10:5000
```

Generar el certificado y levantar:

```bash
./infra/nginx/generar-certificado.sh <IP_PUBLICA_O_DOMINIO>
docker network create torneos_privada
docker compose -f docker-compose.publico.yml up -d
```

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

## 8. Certificado real (cuando haya dominio)

Mientras no hay dominio, el certificado es autofirmado: **cifra de verdad**, pero
el navegador avisa de que no puede verificar la identidad. Con un dominio
apuntando a la IP pública, se sustituye por uno real y gratuito de Let's Encrypt:

```bash
docker run --rm \
  -v ./infra/nginx/certs:/etc/letsencrypt/live/<DOMINIO> \
  -v certbot_www:/var/www/certbot \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d <DOMINIO> --agree-tos -m <CORREO_ADMIN>

docker compose -f docker-compose.publico.yml restart nginx
```

- `<DOMINIO>`: el dominio real apuntando a la Elastic IP (p. ej. `torneos.tuclub.mx`).
- `<CORREO_ADMIN>`: un correo tuyo, para los avisos de expiración de Let's Encrypt.

Certbot escribe `fullchain.pem` y `privkey.pem` en la misma ruta que ya usa
nginx, así que **no hay que tocar la configuración**. El `restart nginx` de
arriba es imprescindible aquí (no es el mismo caso de la sección 7: el
certificado cambió de contenido, no la dirección de un backend). Renovación
automática:

```bash
0 3 * * * cd /home/ec2-user/sistema-futbol && docker run --rm -v ./infra/nginx/certs:/etc/letsencrypt certbot/certbot renew --quiet && docker compose -f docker-compose.publico.yml restart nginx
```

## 9. Comprobación del despliegue

### 9.1 Local, antes de tocar AWS

Antes de repetir estos pasos ya en AWS, corre la validación completa en tu
máquina con los scripts de la sección 4
(`infra/levantar-local.sh`, `infra/verificar-local.sh`,
`infra/restaurar-desarrollo.sh`). Detectar ahí un fallo —una migración que no
corre, un 502 de nginx, una cabecera HSTS duplicada— es mucho más rápido que
depurarlo por SSH contra dos EC2.

### 9.2 Ya en AWS

```bash
curl -k https://<IP_PUBLICA>/api/health          # {"api":"ok","base_de_datos":"ok"}
curl -I http://<IP_PUBLICA>                       # 301 a https
curl -sk -D- -o /dev/null https://<IP_PUBLICA>/ | grep -ci strict-transport   # 1
```

Y que **la privada no se alcanza desde fuera** (esto debe fallar):

```bash
curl --max-time 5 http://10.0.2.10:8001/health   # debe dar timeout
```

---

## Resumen de la verificación

Al terminar la Fase 1, queda demostrado:

| Requisito del PI | Cómo se comprueba |
|---|---|
| Dos servidores (público/privado) | Los dos compose; la privada sin IP pública y con Postgres inalcanzable |
| Certificado SSL | HTTPS responde; HTTP redirige con 301 |
| Balanceador de carga | Ambas réplicas atienden peticiones; se apaga una y el sistema sigue en pie |
| — (arreglo) HSTS | Exactamente una cabecera, no dos |
| — (arreglo) IP real | La auditoría registra la IP del cliente, no la de nginx |
| — (extra) Menor privilegio | La API no es superusuario, no puede hacer DDL, y las migraciones corren en un contenedor efímero aparte |

Pendiente para la **Fase 2**: `ufw` + `fail2ban` (firewall aplicado y
monitoreado), Security Groups ya documentados, Uptime Kuma y healthchecks.
