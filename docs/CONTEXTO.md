# Contexto del proyecto — Sistema-Futbol

> Documento de contexto integral del proyecto al **2026-07-31**.
> Sirve para poner al día a cualquier persona (o agente) que se incorpore al proyecto.

---

## 1. Qué es

**Sistema Integral de Administración de Canchas y Torneos de Fútbol**: plataforma web y móvil para administrar canchas, sedes, torneos, partidos, horarios, pagos y usuarios. Es el **Proyecto Integrador (PI) del Tercer Ciclo**, evaluado contra requerimientos formales de programación móvil y seguridad informática (ver §4).

Repositorio: `~/sistema-torneos/sistema-futbol` (rama principal: `main`, HEAD `fd184e5`, **cero PRs abiertos**, 31 PRs mergeados).

## 2. Stack y componentes

| Parte | Tecnología | Puerto (local) |
|---|---|---|
| API / Backend | Python + **FastAPI** (SQLAlchemy, Alembic, Pydantic) | 8000 |
| Panel web admin | Python + **Flask** (Jinja, CSP estricta) | 5000 |
| App móvil | **React Native + Expo** (SDK 51, Expo Go) | QR / túnel |
| Base de datos | **PostgreSQL 16** | 5432 |
| Proxy / balanceador | **nginx** (TLS, balanceo entre 2 réplicas de API) | 443 |
| Monitoreo | **Uptime Kuma** | 8443 |

Roles de usuario: **superadmin**, **entrenador**, **árbitro**, **jugador**.

### Estructura del repo

```
sistema-futbol/
├── docker-compose.yml            # desarrollo: DB + API + Web
├── docker-compose.publico.yml    # producción: nginx + TLS + kuma (servidor público)
├── docker-compose.privado.yml    # producción: api1/api2 + web + postgres (servidor privado)
├── api/                          # Backend FastAPI
├── web/                          # Panel admin Flask
├── mobile/                       # App React Native + Expo
├── infra/                        # Firewall, fail2ban, simulación local de las 2 VMs
├── brand/                        # Logo maestro + generador de assets (Pillow)
└── docs/                         # DESPLIEGUE.md, PUSH.md, specs superpowers
```

## 3. Arquitectura de producción (DMZ)

Dos servidores exigidos por el PI:

- **Servidor público** (`torneos-publica`): nginx con certificado TLS, balanceador de carga hacia las dos réplicas de API, y Uptime Kuma. Único con IP pública.
- **Servidor privado** (`torneos-privada`): `api1` + `api2` (réplicas FastAPI), panel Flask y PostgreSQL. **Sin IP pública**; sale a internet por NAT.

Decisiones de seguridad clave:
- La API **no es superusuario** de Postgres: usa un usuario limitado sin DDL. Las migraciones corren en un **contenedor efímero** que es el único con credenciales de admin.
- Firewall con **ufw + cadena DOCKER-USER** (Docker se salta ufw si no). **fail2ban** monitorea y banea (jaula extra `torneos-login`).
- Cabeceras de seguridad (CSP estricta, HSTS), rate limit en login (slowapi, 20/min), auditoría de eventos sensibles (`app/audit.py`), SECRET_KEY sin fallback, seed bloqueado en producción.
- Autenticación: **JWT HS256** (`security.py`, `deps.get_current_user`), contraseñas con **bcrypt**, `ACCESS_TOKEN_EXPIRE_MINUTES=720` (parche hasta tener refresh token).

## 4. Requerimientos mínimos del PI (la vara de evaluación)

**Programación móvil**: app de utilidad real (no copia de la web), diseño profesional, navegación clara, **validación de datos en TODAS las interfaces que escriben a la BD**, API propia con BD, y **web+API+BD en la nube**.

**Seguridad informática**: hasheo y encriptación demostrables (bcrypt + JWT ✔), **dos servidores público/privado** ✔, **monitoreo** ✔ (Kuma), **firewall aplicado Y monitoreado** ✔ (ufw + fail2ban), **JWT** ✔, **certificado SSL** ✔ (Let's Encrypt real para `sistemafutbol.com`, con renovación automática), **balanceador de carga** ✔ (nginx → api1/api2).

**Los 6 requisitos están cubiertos y corriendo en la nube.**

## 5. Despliegue en AWS (🚀 hecho el 2026-07-31)

- Región **us-east-1**. VPC `torneos-vpc` 10.0.0.0/16; subred pública 10.0.1.0/24 (IGW) y privada 10.0.2.0/24 (NAT zonal).
- EC2: `torneos-publica` t3.small `10.0.1.10` con **Elastic IP `34.233.0.157`**; `torneos-privada` t3.medium `10.0.2.10` sin IP pública. Ambas **Ubuntu 24.04**.
- SSH vía `~/.ssh/config` con hosts `torneos-publica` y `torneos-privada` (ProxyJump por el bastión público); llave `torneos-llave.pem`.
- Security Groups restringen 22/8443 a la IP de administración del usuario (`187.243.210.132`; si cambia de red hay que editar las 2 reglas y `ADMIN_IP`).
- **Dominio: `sistemafutbol.com`** (Cloudflare Registrar; registro A `@` → Elastic IP, **DNS only** — sin proxy). Certificado **Let's Encrypt** emitido el 2026-08-02 (sección 11 de `DESPLIEGUE.md`); el 8443 sirve el mismo. Renovación: cron diario de root a las 3:00 con `infra/nginx/renovar-certificado.sh` (⚠️ el script necesita `sudo`: certbot deja `live/` como root 0700), log en `/var/log/certbot-renovacion.log`.
- Batería final de verificación en verde: health E2E, redirección 301, HSTS única, API y Postgres inalcanzables en directo. Kuma con 4 monitores verdes en `https://sistemafutbol.com:8443`.
- Superadmin de producción: `vikcaballero86@gmail.com` (la BD nace sin roles porque el seed aborta en producción; se creó con guion Python vía `docker compose exec api1`).
- Costo: ~$2.5–3 USD/día (NAT + 2 EC2). Pausar = Stop de las EC2 (el NAT sigue cobrando salvo borrarlo).

**Trampas reales de Ubuntu 24.04 / consola AWS** (documentadas en `docs/DESPLIEGUE.md`, PR #31):
- `ufw` es **incompatible** con `iptables-persistent` en 24.04 → la persistencia del firewall es una unidad systemd `torneos-firewall.service` (oneshot, After=docker.service) que re-corre `configurar-firewall.sh` en cada arranque.
- El asistente nuevo de NAT pide tipo "Zonal"; borrar un NAT deja una EIP huérfana que cobra.
- Quick Start preselecciona una AMI "with SQL Server" **de pago** — evitarla.
- AWS prohíbe nombres de Security Group que empiecen con "sg-".
- Redes con CGNAT/IPv6 rompen las reglas de admin por IP.

## 6. Estado actual y pendientes

### Pendiente inmediato
**Nada bloqueante — el sistema está completo en producción (2026-08-02).** El dominio `sistemafutbol.com` con Let's Encrypt cerró lo último que faltaba, con sus tres remates:
- Monitor E2E de Kuma reapuntado a `https://sistemafutbol.com/api/health`, sin "Ignore TLS" y con aviso de caducidad del certificado.
- **App móvil validada contra producción** con `EXPO_PUBLIC_API_URL=https://sistemafutbol.com/api` (con `/api` y sin barra final — nginx quita el prefijo; para builds EAS la variable va en `eas.json` o como secret, no en `.env`).
- Candado disponible para la Figura 5 del `ED0302-JWT-SSL.docx` (tarea ED.03.02).

### Deuda técnica abierta (por prioridad)
- **Lock de fila (`with_for_update`) en la guardia del doble pago** — con 2 réplicas de API la carrera es real (el 2º commit da 500 en vez de 409).
- **Refresh token real** — los 720 min del access token son un parche; al implementarlo, bajar el valor también en el `.env` de producción.
- `subirFoto` móvil usa `fetch` crudo sin timeout.
- Ampliar `mobile/scripts/verificar-nombres-iconos.cjs` para reconocer la prop `icono` (2 puntos de render ciegos) y acotar la regex al componente `<Icono>`.
- `guardar_plan` no valida `len(jugadores) <= suma(formación)`.
- Higiene menor: autogol acredita asistencia, `UsuarioOut` duplicado, `LineupScreen` acepta 0 jugadores, cupo de inscripción cuenta todos los estados (TOCTOU), etc.

### Historial de PRs (resumen)
| PRs | Qué |
|---|---|
| #9–#12 | Deuda de seguridad RNF-02: SECRET_KEY, rate limit, seed vs producción, CSP/HSTS, auditoría |
| #13–#14 | Infra de producción: DMZ 2 servidores, réplicas API, firewall, fail2ban, Kuma, healthchecks |
| #15 | Validación de datos en las 9 pantallas móviles que escriben a la BD |
| #16 | Notificaciones push (IF-11): Expo Push + BD como respaldo por polling |
| #17–#18 | Pulido web, branding (logo en `brand/`), iconos Reicon en el menú web (SVG inline, sin CDN por la CSP) |
| #19 | Deuda: N+1 (`CARGA_*`), 12 índices FK, `deps.es_admin` único, reglas de reserva/alineación, sesión 720 min |
| #20–#23 | Fotos de perfil (Pillow 512² JPEG), alineaciones visuales (cancha 2:3), iconos vectoriales móviles — cero emojis de color |
| #24 | Reglas del partido en vivo: doble amarilla expulsa, `en_campo`, minuto obligatorio |
| #25 | Cascadas ORM en `Partido` (DELETE con alineación daba 500) + banca del detalle web |
| #26–#28 | Serie nocturna: reservas del entrenador, inscripciones a torneos, notificaciones árbitro/entrenador |
| #29 | Icono de calendario invisible en inputs oscuros (filtro CSS) |
| #30 | `apiUrl` móvil → `EXPO_PUBLIC_API_URL` (la IP local vive en `mobile/.env`, ignorado) |
| #31 | `docs/DESPLIEGUE.md` corregido con las lecciones del despliegue real |

**Suite de tests: 279/279 en verde (~7 min)** gracias al fixture `_sin_push` (los tests de push real optan con el marker `usa_push`).

## 7. Desarrollo local

```bash
docker compose up -d                                # DB + API + Web
docker compose exec api alembic upgrade head        # migrar (SIEMPRE dentro del contenedor)
docker compose exec api python -m app.seed          # sembrar datos demo
```

- ⚠️ Alembic va **dentro del contenedor**: `.env` tiene `DB_HOST=db`, que solo resuelve en la red de Docker. Desde el host: prefijar `DB_HOST=localhost`.
- Migraciones **colapsadas a un baseline único** (`esquema_inicial`, `ac4f76d969b7`); BDs selladas en revisiones viejas deben recrearse.
- Credenciales demo del seed: `superadmin@demo.com` / `admin1234`; `entrenador@`, `arbitro@`, `jugador@demo.com` / `demo1234`.

**Móvil**: `cd mobile && npm install && npx expo start --tunnel` (WSL2 del dev no soporta red mirrored). La URL de la API sale de `EXPO_PUBLIC_API_URL` en `mobile/.env` (plantilla en `mobile/.env.example`).

**Simulación local de la infra de producción** (no toca la BD de desarrollo — proyecto Docker `torneos-prod`):
```bash
./infra/levantar-local.sh       # simula las dos VMs
./infra/verificar-local.sh      # 15 comprobaciones, todas deben pasar
./infra/restaurar-desarrollo.sh
```

### Verificadores del móvil
- `npm run verificar` — sintaxis con el `@babel/core` del proyecto. ⚠️ **`npx babel` NO sirve** (resuelve al paquete `babel` v6 deprecado y falla con archivos válidos).
- `npm run verificar-iconos` y `npm run verificar-nombres` — integridad del catálogo de 20 iconos (una errata en un nombre pinta un hueco invisible, no lanza error).
- ⚠️ No hay navegador headless en el entorno: los cambios de CSS requieren comprobación visual del usuario.

## 8. Flujo de trabajo

- Nadie trabaja directo en `main`: rama `feat/...` / `fix/...` / `docs/...` → PR → revisión → merge.
- **Pedir aprobación del usuario antes de cualquier commit, push o PR.**
- La suite de Python tarda ~7 min (contar con ello al planificar).

## 9. Decisiones de diseño y trampas conocidas (no re-descubrir)

- **Iconos**: web = SVG inline vía macro Jinja `_iconos.html` (la CSP bloquea CDNs); móvil = `<Icono>` con `react-native-svg` alimentado por `iconos-datos.json`, **generado** por `mobile/scripts/generar-iconos.cjs` (no transcrito a mano — `calendar` trae 7 paths y perder uno no da error).
- **`EditarPerfilModal` no lleva `useEffect` de sincronización a propósito** (documentado en la cabecera del archivo): un efecto pisaría lo que el usuario escribe cuando `refrescar()` cambia la prop.
- `Distintivos` se pinta sobre dos fondos (cancha y banca); el color base es la prop `tinte`.
- Hay eventos legítimos **sin `jugador_id`** (autogol atribuido al equipo); el fallback "equipo sin alineación = plantilla entera elegible" sostiene los tests de eventos.
- La columna `minuto` NO es NOT NULL a propósito (fila legada `id=12`); la obligatoriedad vive en Pydantic (422).
- El cierre de inscripciones se compara como cadena ISO local — `new Date("YYYY-MM-DD")` es medianoche UTC y correría el cierre un día.
- Las cascadas de borrado de `Partido` son **a nivel ORM** (sin migración): un DELETE a mano en SQL choca con la FK.
- Todos los `jugador_id` (eventos, plantilla, plan) son `usuarios.id` — las fotos resuelven en `/usuarios/{id}/foto`.
- RN `<Image source={{headers}}>` no envía Authorization fiablemente → los avatares descargan con `FileSystem.downloadAsync`.
- Al planificar reglas de negocio, preguntarse qué pasa al **deshacer** cada acción nueva (los 2 bugs del PR #24 salieron de interacciones con `DELETE /eventos`).

## 10. Documentación de referencia

- `docs/DESPLIEGUE.md` — guía de despliegue AWS, corregida con la experiencia real (Ubuntu 24.04).
- `docs/PUSH.md` — demo de notificaciones push en dispositivo real (requiere build EAS).
- `docs/superpowers/` — specs y planes de los PRs mayores.
- `MANUAL_INTERFACES.md` — manual de interfaces.
- `mobile/README.md` — flujo de `EXPO_PUBLIC_API_URL`.
