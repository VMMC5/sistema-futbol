# Correo real de credenciales vía Brevo

**Fecha:** 2026-08-02
**Estado:** aprobado por el usuario (diseño validado en conversación)

## Objetivo

Cuando un entrenador o árbitro envía una solicitud de cuenta y el superadmin la
acepta, el sistema debe mandarle un **correo real** con su contraseña temporal,
que la app le obliga a cambiar en el primer inicio de sesión.

## Punto de partida (lo que YA existe — no reimplementar)

El flujo completo ya está en el código; hoy solo está "dormido" porque
producción no tiene SMTP configurado:

- `api/app/routers/solicitudes.py` — `aceptar_solicitud` crea el usuario con
  contraseña temporal (`secrets.token_urlsafe(9)`), marca
  `debe_cambiar_password=True` y llama a `enviar_correo` con las credenciales.
  `rechazar_solicitud` también envía correo (con el motivo).
- `api/app/email_utils.py` — `enviar_correo` manda correo real por SMTP si
  existen las variables `SMTP_*`; sin ellas imprime el correo en consola
  (modo desarrollo). Esa dualidad se conserva tal cual.
- `api/app/routers/auth.py` — el login devuelve `debe_cambiar_password` y
  `PUT /auth/password` lo apaga; el móvil (`auth.js`) ya recibe `debeCambiar`.

## Lo que falta

### A. Configuración (sin código)

1. Cuenta gratuita en **Brevo** (300 correos/día, de sobra).
2. **Autenticar el dominio** `sistemafutbol.com` en Brevo: agrega en Cloudflare
   los registros DNS que Brevo indique (verificación + DKIM), como **DNS only**.
   Con eso el remitente `no-reply@sistemafutbol.com` no cae a spam.
3. Generar una **clave SMTP** en Brevo y añadir al `.env` del **servidor
   privado** (api1/api2; salen por NAT al puerto 587, sin tocar Security Groups):

   ```
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=<login SMTP de Brevo>
   SMTP_PASSWORD=<clave SMTP de Brevo>
   SMTP_FROM=Sistema de Torneos <no-reply@sistemafutbol.com>
   ```

4. Documentar: las 5 variables comentadas en `.env.example` y una nota en
   `docs/DESPLIEGUE.md`.

### B. Endurecimiento del código (2 archivos)

El envío hoy es inofensivo porque está simulado; con SMTP real aparecen dos
modos de falla que hay que cerrar **antes** de configurar Brevo:

1. **`email_utils.py`**: `smtplib.SMTP(host, puerto)` → agregar `timeout=10`.
   Sin él, un SMTP colgado congela la petición del admin y ocupa un worker.
   Único cambio en el archivo.
2. **`solicitudes.py`**: `aceptar_solicitud` y `rechazar_solicitud` reciben
   `background_tasks: BackgroundTasks` y encolan el correo con
   `background_tasks.add_task(enviar_correo, ...)` en vez de llamarlo inline.
   Mismo patrón best-effort que las push (`notificaciones_service`). Motiva el
   cambio un modo de falla real: el correo se envía **después del commit**; si
   el SMTP falla inline, el admin recibe 500 con el usuario YA creado, y el
   reintento le da "Ya existe un usuario con ese correo".

### Manejo de errores (decisión consciente)

Best-effort: si el envío en background falla, se loguea el error **sin PII y
sin la contraseña temporal** (mismo criterio que `enviar_push`) y la aceptación
queda firme. Sin reintentos ni cola persistente — YAGNI a esta escala; si algún
día duele, se anota como deuda. Vía de recuperación manual: el log del
contenedor.

## Tests

- Los tests existentes de solicitudes deben seguir pasando sin cambios (sin
  `SMTP_HOST` rige el modo simulado; `TestClient` ejecuta los background tasks
  tras la respuesta).
- **Nuevos:**
  1. Aceptar una solicitud encola el correo: mock de `enviar_correo`,
     verificar destinatario y que la contraseña temporal viaja en el cuerpo.
  2. Si `enviar_correo` lanza excepción, la aceptación responde **200** igual y
     el usuario queda creado (el modo de falla que motivó el diseño).

## Despliegue y verificación

1. Merge del PR → en `torneos-privada`: `git pull` + rebuild de api1/api2.
2. Editar `.env` (5 variables) + `up -d` para recrear contenedores.
3. Prueba real de punta a punta: solicitud desde la app con un correo propio →
   aceptar desde el panel → recibir el correo → login con la contraseña
   temporal → la app fuerza el cambio → login normal.

## Fuera de alcance

- Reintentos / cola persistente de correo.
- Plantillas HTML de correo (el texto plano actual se conserva).
- Correos para otros eventos (invitaciones, pagos… siguen como están).
