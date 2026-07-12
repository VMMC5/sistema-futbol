# Diseño — Infraestructura de producción

Fecha: 2026-07-11
Estado: propuesto

## Objetivo

Desplegar `sistema-futbol` en AWS cumpliendo los **Requerimientos Mínimos del PI**
(sección "Seguridad Informática"), que hoy no se cumplen:

| Requisito | Estado hoy |
|---|---|
| Al menos dos servidores: uno público y otro privado | ❌ un solo `docker-compose` |
| Certificado SSL para la plataforma | ❌ todo por HTTP plano |
| Uso de balanceador de carga | ❌ no existe |
| Aplicación **y monitoreo** de Firewall | ❌ no existe |
| Monitoreo del sistema | ❌ no existe |
| Protección de API con JWT | ✅ hecho |
| Métodos de hasheado y encriptado | ✅ hecho (bcrypt + JWT) |

Se aprovecha además para cerrar la última brecha de seguridad pendiente: la
aplicación corre hoy como `postgres`, **superusuario** de la base de datos.

## Restricciones

- **Proveedor:** AWS, dos instancias EC2 (decidido).
- **Dominio:** todavía no existe, pero lo habrá. El diseño debe funcionar ya con
  certificado autofirmado y permitir pasar a Let's Encrypt sin rehacer nada.
- **Sin reescribir la aplicación.** Se conserva `docker-compose`; no se migra a
  ECS/Fargate ni a servicios gestionados.
- **Verificable en local.** Todo debe poder levantarse y probarse en la máquina
  del desarrollador antes de tocar AWS.

## Arquitectura

```
                        Internet
                           │
                        :443 TLS
                           │
   ┌───────────────────────▼─────────────────────────┐
   │  EC2 PÚBLICA — subred pública, con IP pública    │
   │                                                  │
   │   nginx        · termina TLS/SSL + HSTS          │
   │                · BALANCEADOR (upstream)          │
   │                · único punto de entrada          │
   │   Uptime Kuma  · monitoreo (fase 2)              │
   │   ufw + fail2ban · firewall (fase 2)             │
   └───────────────────────┬─────────────────────────┘
                           │ red privada de la VPC
                           │ (la privada no tiene ruta a internet)
   ┌───────────────────────▼─────────────────────────┐
   │  EC2 PRIVADA — subred privada, SIN IP pública    │
   │                                                  │
   │   API réplica 1  :8001  ┐                        │
   │   API réplica 2  :8002  ┘ ← balanceadas          │
   │   Panel Flask    :5000                           │
   │   PostgreSQL     :5432   (nunca sale de la VM)   │
   │   ufw            · firewall (fase 2)             │
   └──────────────────────────────────────────────────┘
```

La EC2 privada **no es alcanzable desde internet**: no tiene IP pública y su
Security Group solo admite tráfico originado en la EC2 pública. Esa separación
es la que exige el requisito de "un servidor de acceso público y otro privado".

### Enrutado en nginx

| Ruta | Destino |
|---|---|
| `https://host/` | Panel web (Flask) |
| `https://host/api/` | API — repartida entre las dos réplicas |
| `https://host/monitor` | Uptime Kuma (fase 2) |

La app móvil pasa a apuntar a `https://host/api`. Su `API_URL` ya es
configurable, así que no requiere cambios de código.

### El balanceador es real, no decorativo

nginx declara un `upstream` con **dos réplicas de la API** corriendo de verdad.
Se puede detener una y comprobar que el sistema sigue respondiendo. No es un
proxy a un único backend disfrazado de balanceador.

### Portabilidad local ↔ AWS

nginx no lleva las direcciones escritas a mano. Usa las plantillas con
`envsubst` que trae la imagen oficial (`/etc/nginx/templates/*.template`), y las
réplicas se inyectan por entorno:

- **En local:** `API_1=api1:8000`, `API_2=api2:8000` (nombres de contenedor).
- **En AWS:** `API_1=10.0.2.10:8001`, `API_2=10.0.2.10:8002` (IP privada de la
  otra EC2).

El mismo `nginx.conf` sirve en los dos sitios. Sin ediciones manuales, que es
justo donde se cuelan los errores al desplegar.

## Componentes

### `docker-compose.publico.yml` (EC2 pública)
- `nginx`: puertos 80 y 443. El 80 solo redirige a 443 (y sirve el desafío
  HTTP-01 de certbot cuando llegue el dominio).
- (Fase 2) `uptime-kuma`.

### `docker-compose.privado.yml` (EC2 privada)
- `api1`, `api2`: dos contenedores de la API. Sustituyen al servicio `api`
  único de `docker-compose.prod.yml`.
- `web`: panel Flask con gunicorn.
- `db`: PostgreSQL, sin publicar puertos.

`docker-compose.prod.yml` (el actual) queda **obsoleto** y se elimina: su
contenido se reparte entre estos dos.

### TLS

- **Ahora:** script que genera un certificado autofirmado en `nginx/certs/`.
  Cifra de verdad; el navegador avisará de que no está firmado por una CA
  conocida, lo cual es esperado sin dominio.
- **Cuando haya dominio:** un servicio `certbot` documentado y listo para
  emitir el certificado real de Let's Encrypt y renovarlo. Los ficheros caen en
  la misma ruta, así que nginx no cambia.

#### HSTS: una sola cabecera, la de nginx

Cuidado con una trampa. El grupo D ya hace que **la API y el panel emitan
`Strict-Transport-Security`** cuando `APP_ENV=production` — y en producción esa
variable debe estar puesta, porque también activa la barrera del seed.

Si nginx añadiera la suya, el cliente recibiría **dos cabeceras HSTS**. Ante eso
los navegadores descartan la política entera, y el requisito quedaría incumplido
justo cuando parece cumplido.

Solución: nginx, que es quien termina el TLS, es el **único dueño** de HSTS:

```nginx
proxy_hide_header Strict-Transport-Security;   # descarta la de la app
add_header Strict-Transport-Security "..." always;   # emite la suya
```

Se verifica contando las cabeceras de la respuesta: debe haber exactamente una.

### Usuario de base de datos con menor privilegio

Hoy la API se conecta como `postgres` (superusuario). Se separan dos roles:

| Rol | Quién lo usa | Permisos |
|---|---|---|
| `DB_ADMIN_USER` | Migraciones de Alembic | Dueño del esquema (DDL) |
| `DB_USER` | La API en runtime | Solo `SELECT/INSERT/UPDATE/DELETE` |

Un script de init crea el rol limitado y, **antes** de que corran las
migraciones, fija `ALTER DEFAULT PRIVILEGES`. Así las tablas que Alembic cree
después quedan automáticamente accesibles al usuario de la API, sin tener que
re-otorgar permisos tras cada migración — que es el error clásico de este
montaje.

`app/database.py` sigue leyendo `DB_USER`/`DB_PASSWORD`, que ahora son los del
usuario limitado. `migrations/env.py` pasa a usar las variables de admin.

**Consecuencia:** los scripts de init de Postgres solo corren con un volumen
nuevo. La base de producción se crea desde cero, así que no hay problema. El
entorno local **no se toca**: sigue con `postgres` en `docker-compose.yml`.

## Fases

### Fase 1 — Servidores, SSL, balanceador y usuario de BD
1. Separar en `docker-compose.publico.yml` y `docker-compose.privado.yml`.
2. nginx: TLS, HSTS, redirección 80→443, `upstream` con dos réplicas.
3. Script de certificado autofirmado + ruta a certbot documentada.
4. Usuario de BD con menor privilegio (init SQL + `env.py` de Alembic).
5. Verificación en local simulando las dos VMs.

### Fase 2 — Firewall y monitoreo
1. `ufw` en ambas VMs (script idempotente) con logging activado.
2. `fail2ban` vigilando SSH y nginx: aplica **y monitorea** el firewall.
3. Security Groups de AWS documentados (la capa de firewall del proveedor).
4. Uptime Kuma: vigila nginx, las dos réplicas de la API, el panel y Postgres.
5. Healthchecks de Docker en todos los servicios.

## Verificación

**En local, antes de tocar AWS.** Los dos compose se levantan en la misma
máquina unidos por una red Docker externa que simula la red privada de la VPC.
Se comprueba:

- HTTPS responde y el HTTP redirige a HTTPS.
- El panel y la API funcionan a través de nginx (login end-to-end).
- **El balanceo reparte de verdad**: se apaga una réplica y el sistema sigue
  respondiendo.
- **Exactamente una cabecera HSTS** en la respuesta (ver la trampa de arriba).
- Postgres no es accesible desde fuera.
- La API funciona con el usuario limitado, y **falla** si intenta un DDL.
- Los 192 tests siguen en verde.

**En AWS**, con una guía de despliegue paso a paso: VPC, subredes, Security
Groups, las dos EC2 y el arranque de cada compose.

## Fuera de alcance

- Migrar a ECS/Fargate o RDS (se conserva docker-compose, por decisión).
- Certificado de Let's Encrypt emitido: requiere el dominio, que aún no existe.
  Queda todo listo y documentado.
- Notificaciones push (IF-11) y la deuda menor del módulo de pagos.
- Auditar la validación de datos en la app móvil (requisito del PI, frente
  aparte).
