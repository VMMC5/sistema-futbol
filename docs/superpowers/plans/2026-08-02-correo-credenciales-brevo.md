# Correo real de credenciales (Brevo) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer el envío de correo (timeout + best-effort en background) para poder conectar SMTP real de Brevo en producción sin nuevos modos de falla.

**Architecture:** El flujo funcional ya existe (`aceptar_solicitud` crea usuario con contraseña temporal y llama `enviar_correo`; `email_utils` decide real/simulado según `SMTP_*`). Este plan solo: (1) agrega `timeout` al SMTP y un envoltorio `enviar_correo_seguro` que nunca propaga, (2) mueve los dos envíos de `solicitudes.py` a `BackgroundTasks` (mismo patrón que las push), (3) documenta las variables. La configuración de Brevo/DNS es manual post-merge (ver spec).

**Tech Stack:** FastAPI (BackgroundTasks), smtplib, pytest. Spec: `docs/superpowers/specs/2026-08-02-correo-credenciales-brevo-design.md`.

## Global Constraints

- Rama de trabajo: `feat/correo-credenciales-brevo` (ya creada, spec commiteado).
- Tests desde `api/` con el venv del proyecto: `.venv/bin/pytest` (NO usar `npx babel` ni el venv desde fuera de `api/`).
- Los logs de correo NUNCA incluyen destinatario ni cuerpo (el cuerpo lleva la contraseña temporal). Solo asunto y tipo de excepción.
- El modo simulado (sin `SMTP_HOST` ⇒ print en consola) se conserva idéntico: los tests existentes dependen de él.
- No tocar el texto de los correos ni el flujo de `debe_cambiar_password` — ya existen y están probados (`test_flujo_completo_aceptar_y_cambio_forzado`).

---

### Task 1: `email_utils` — timeout y envoltorio best-effort

**Files:**
- Modify: `api/app/email_utils.py`
- Test: `api/tests/test_email_utils.py` (nuevo)

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `enviar_correo_seguro(destinatario: str, asunto: str, cuerpo: str) -> None` — misma firma que `enviar_correo`, pero atrapa cualquier excepción y la loguea sin PII. La Task 2 lo encola en `BackgroundTasks`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `api/tests/test_email_utils.py`:

```python
"""Pruebas de email_utils: timeout del SMTP y el envoltorio best-effort."""
import smtplib

from app import email_utils


class _SMTPFalso:
    """Captura los argumentos de smtplib.SMTP sin abrir conexiones."""

    ultimo = None

    def __init__(self, host, puerto, timeout=None):
        _SMTPFalso.ultimo = {"host": host, "puerto": puerto, "timeout": timeout}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, usuario, password):
        pass

    def send_message(self, mensaje):
        pass


def test_smtp_real_lleva_timeout(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.ejemplo.com")
    monkeypatch.setattr(smtplib, "SMTP", _SMTPFalso)
    email_utils.enviar_correo("a@demo.com", "Asunto", "Cuerpo")
    assert _SMTPFalso.ultimo["timeout"] == 10


def test_sin_smtp_no_toca_la_red(monkeypatch, capsys):
    monkeypatch.delenv("SMTP_HOST", raising=False)

    def _explota(*args, **kwargs):
        raise AssertionError("sin SMTP_HOST no debe abrirse conexión")

    monkeypatch.setattr(smtplib, "SMTP", _explota)
    email_utils.enviar_correo("a@demo.com", "Asunto", "Cuerpo")
    assert "CORREO SIMULADO" in capsys.readouterr().out


def test_enviar_correo_seguro_atrapa_y_loguea_sin_pii(monkeypatch, caplog):
    def _smtp_caido(*args, **kwargs):
        raise RuntimeError("smtp caído")

    monkeypatch.setattr(email_utils, "enviar_correo", _smtp_caido)
    with caplog.at_level("ERROR"):
        # No debe lanzar:
        email_utils.enviar_correo_seguro("secreto@demo.com", "Asunto X", "cuerpo con password")
    assert "RuntimeError" in caplog.text
    assert "secreto@demo.com" not in caplog.text
    assert "password" not in caplog.text
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_email_utils.py -v`
Expected: `test_smtp_real_lleva_timeout` FALLA (timeout es None) y `test_enviar_correo_seguro_atrapa_y_loguea_sin_pii` FALLA con `AttributeError: enviar_correo_seguro`. `test_sin_smtp_no_toca_la_red` puede pasar ya (documenta el contrato actual).

- [ ] **Step 3: Implementar**

En `api/app/email_utils.py`:

1. Junto a los imports, agregar:

```python
import logging

logger = logging.getLogger(__name__)

# Segundos máximos esperando al servidor SMTP. Sin esto, un SMTP colgado
# congela la petición (o el background task) indefinidamente.
SMTP_TIMEOUT = 10
```

2. Cambiar la línea `with smtplib.SMTP(host, puerto) as servidor:` por:

```python
    with smtplib.SMTP(host, puerto, timeout=SMTP_TIMEOUT) as servidor:
```

3. Al final del archivo, agregar:

```python
def enviar_correo_seguro(destinatario: str, asunto: str, cuerpo: str) -> None:
    """Variante best-effort para BackgroundTasks: nunca propaga.

    Si el envío falla, el error se loguea SIN el destinatario ni el cuerpo
    (el cuerpo puede llevar una contraseña temporal); la operación que lo
    encoló (p. ej. aceptar una solicitud) ya quedó firme en la BD.
    """
    try:
        enviar_correo(destinatario, asunto, cuerpo)
    except Exception as exc:  # consciente: best-effort, igual que enviar_push
        logger.error("Fallo el envio de correo '%s': %s", asunto, type(exc).__name__)
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd api && .venv/bin/pytest tests/test_email_utils.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/email_utils.py api/tests/test_email_utils.py
git commit -m "feat(api): timeout SMTP y envio de correo best-effort"
```

---

### Task 2: `solicitudes` — el correo sale en background

**Files:**
- Modify: `api/app/routers/solicitudes.py` (imports; `aceptar_solicitud` líneas ~122-176; `rechazar_solicitud` líneas ~179-211)
- Test: `api/tests/test_solicitudes.py` (agregar 2 tests al final)

**Interfaces:**
- Consumes: `enviar_correo_seguro(destinatario, asunto, cuerpo)` de Task 1 (import: `from app.email_utils import enviar_correo_seguro`).
- Produces: sin cambios de contrato HTTP — mismas rutas, mismos schemas de respuesta.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `api/tests/test_solicitudes.py` (usa el helper `_crear_solicitud` y la fixture `auth_admin` ya existentes en ese archivo):

```python
def test_aceptar_encola_correo_con_credenciales(client, auth_admin, monkeypatch):
    import app.routers.solicitudes as mod
    monkeypatch.setattr(mod.secrets, "token_urlsafe", lambda n=9: "TempCorreo789")
    enviados = []
    monkeypatch.setattr(
        mod, "enviar_correo_seguro",
        lambda destinatario, asunto, cuerpo: enviados.append((destinatario, asunto, cuerpo)),
    )

    sid = _crear_solicitud(client, correo="correo.real@demo.com").json()["id"]
    r = client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin)
    assert r.status_code == 200

    # TestClient ejecuta los background tasks antes de devolver la respuesta
    assert len(enviados) == 1
    destinatario, _asunto, cuerpo = enviados[0]
    assert destinatario == "correo.real@demo.com"
    assert "TempCorreo789" in cuerpo


def test_aceptar_sobrevive_a_fallo_de_correo(client, auth_admin, monkeypatch):
    # Se rompe enviar_correo (la capa interna): enviar_correo_seguro debe atrapar
    from app import email_utils

    def _smtp_caido(*args, **kwargs):
        raise RuntimeError("smtp caído")

    monkeypatch.setattr(email_utils, "enviar_correo", _smtp_caido)

    sid = _crear_solicitud(client, correo="sin.correo@demo.com").json()["id"]
    r = client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin)
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"

    # El usuario quedó creado pese al fallo del correo: una nueva solicitud
    # con ese correo choca con "Ese correo ya tiene una cuenta".
    r2 = _crear_solicitud(client, correo="sin.correo@demo.com")
    assert r2.status_code == 400
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_solicitudes.py -v`
Expected: `test_aceptar_encola_correo_con_credenciales` FALLA con `AttributeError` (el módulo aún no tiene `enviar_correo_seguro`); `test_aceptar_sobrevive_a_fallo_de_correo` FALLA (el `enviar_correo` inline propaga el RuntimeError). Los 7 tests previos del archivo siguen PASS.

- [ ] **Step 3: Implementar**

En `api/app/routers/solicitudes.py`:

1. En el import de fastapi, agregar `BackgroundTasks` a la lista.
2. Cambiar `from app.email_utils import enviar_correo` por `from app.email_utils import enviar_correo_seguro`.
3. En `aceptar_solicitud`, agregar el parámetro (va antes de los que llevan default):

```python
def aceptar_solicitud(
    solicitud_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
```

4. Reemplazar la llamada `enviar_correo(` de `aceptar_solicitud` por:

```python
    # Correo con las credenciales temporales — en background y best-effort:
    # la aceptación ya quedó firme; un SMTP caído no debe convertirla en 500.
    background_tasks.add_task(
        enviar_correo_seguro,
        destinatario=solicitud.correo,
        asunto="Tu cuenta en el Sistema de Torneos ha sido aprobada",
        cuerpo=(
            f"Hola {solicitud.nombre},\n\n"
            f"Tu solicitud como {solicitud.rol_solicitado} fue aprobada.\n\n"
            f"Para iniciar sesión en la app usa:\n"
            f"  Correo: {solicitud.correo}\n"
            f"  Contraseña temporal: {password_temporal}\n\n"
            f"Por seguridad, el sistema te pedirá cambiar esta contraseña "
            f"la primera vez que inicies sesión.\n\n"
            f"Saludos,\nEquipo de Torneos"
        ),
    )
```

5. En `rechazar_solicitud`, agregar el mismo parámetro `background_tasks: BackgroundTasks` (tras `datos: RechazoSolicitud`) y reemplazar su `enviar_correo(` por:

```python
    background_tasks.add_task(
        enviar_correo_seguro,
        destinatario=solicitud.correo,
        asunto="Sobre tu solicitud en el Sistema de Torneos",
        cuerpo=(
            f"Hola {solicitud.nombre},\n\n"
            f"Lamentamos informarte que tu solicitud no fue aprobada en esta ocasión."
            + (f"\nMotivo: {datos.motivo}" if datos.motivo else "")
            + "\n\nSaludos,\nEquipo de Torneos"
        ),
    )
```

(El texto de ambos correos es EXACTAMENTE el actual — solo cambia cómo se envía.)

- [ ] **Step 4: Verificar que pasan (el archivo entero)**

Run: `cd api && .venv/bin/pytest tests/test_solicitudes.py tests/test_email_utils.py -v`
Expected: todos PASS (7 previos + 2 nuevos + 3 de Task 1). En particular `test_flujo_completo_aceptar_y_cambio_forzado` sigue PASS sin cambios.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/solicitudes.py api/tests/test_solicitudes.py
git commit -m "feat(api): el correo de solicitudes sale en background (best-effort)"
```

---

### Task 3: Documentación de las variables SMTP

**Files:**
- Modify: `.env.example` (nueva sección antes de `# ---------- Pagos`)
- Modify: `docs/DESPLIEGUE.md` (sección 5, tras el párrafo de `DB_NAME`, ~línea 186)

**Interfaces:** ninguna (solo docs).

- [ ] **Step 1: `.env.example`**

Insertar ANTES de la sección `# ---------- Pagos (rellenar cuando integren la pasarela) ----------`:

```
# ---------- Correo (SMTP) ----------
# Sin estas variables, los correos se SIMULAN: se imprimen en el log del
# contenedor de la API (modo normal en desarrollo). En producción se rellenan
# con el relay de Brevo para envío real (ver docs/DESPLIEGUE.md, sección 5).
# El remitente exige el dominio autenticado en Brevo (DNS en Cloudflare).
# SMTP_HOST=smtp-relay.brevo.com
# SMTP_PORT=587
# SMTP_USER=<login SMTP de Brevo>
# SMTP_PASSWORD=<clave SMTP de Brevo>
# SMTP_FROM=Sistema de Torneos <no-reply@sistemafutbol.com>

```

- [ ] **Step 2: `docs/DESPLIEGUE.md`**

En la sección 5, después del párrafo que empieza con «`DB_NAME` ya viene con el valor por defecto», insertar:

```markdown
El correo saliente (credenciales de entrenadores/árbitros aprobados o
rechazados) es opcional pero recomendado: sin las `SMTP_*` los correos solo se
imprimen en el log de la API. Con una cuenta gratuita de Brevo (300/día) y el
dominio autenticado (Brevo da los registros de verificación y DKIM; se agregan
en Cloudflare como **DNS only**), se añaden al mismo `.env`:

    SMTP_HOST=smtp-relay.brevo.com
    SMTP_PORT=587
    SMTP_USER=<login SMTP de Brevo>
    SMTP_PASSWORD=<clave SMTP de Brevo>
    SMTP_FROM=Sistema de Torneos <no-reply@sistemafutbol.com>

El envío sale de las réplicas de la API por el NAT (puerto 587): no hay que
tocar Security Groups. Tras editar el `.env`, recrear los contenedores con
`up -d` (no hace falta rebuild).
```

(Ojo: el bloque de variables va con sangría de 4 espacios — dentro de DESPLIEGUE.md no debe abrir un fence nuevo porque la sección ya usa fences para otros bloques.)

- [ ] **Step 3: Verificar**

Run: `grep -c "SMTP_" .env.example docs/DESPLIEGUE.md`
Expected: 5 o más ocurrencias en cada archivo.

- [ ] **Step 4: Commit**

```bash
git add .env.example docs/DESPLIEGUE.md
git commit -m "docs: variables SMTP (Brevo) en .env.example y guia de despliegue"
```

---

### Task 4: Verificación final y PR

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa de la API**

Run: `cd api && .venv/bin/pytest -q`
Expected: **todos en verde** (279 previos + 5 nuevos = 284). Tarda ~7 min; contar con ello.

- [ ] **Step 2: Push y PR**

⚠️ Regla del proyecto: pedir aprobación del usuario antes del push/PR si no la dio ya.

```bash
git push -u origin feat/correo-credenciales-brevo
gh pr create --title "Correo real de credenciales vía Brevo (endurecimiento SMTP)" --body "..."
```

El cuerpo del PR debe resumir: timeout SMTP, envío en background best-effort, docs de las 5 variables; y remitir al spec para la configuración manual de Brevo/DNS post-merge.
