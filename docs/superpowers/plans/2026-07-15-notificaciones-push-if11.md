# Notificaciones push (IF-11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir notificaciones push reales a la app móvil, disparadas desde un helper central que envía vía Expo Push Service usando FastAPI BackgroundTasks, sin retirar el sistema actual de notificaciones en BD + polling.

**Architecture:** Un servicio backend nuevo (`notificaciones_service.py`) centraliza la creación de notificaciones: inserta la fila en BD (comportamiento actual) y encola el envío push como `BackgroundTasks`. La tarea de envío abre su propia sesión (la del request ya está cerrada al ejecutarse), llama a la Expo Push API con httpx y purga tokens inválidos. El móvil registra su Expo push token vía un endpoint nuevo y monta manejadores de `expo-notifications`.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + httpx (backend); Expo SDK 51 + expo-notifications + expo-device (móvil). Tests con pytest sobre SQLite en memoria.

## Global Constraints

- Entrega push vía **FastAPI `BackgroundTasks`** (nunca síncrono en el request).
- Envío **best-effort**: cualquier fallo de push se traga con try/except y NUNCA rompe la creación de la notificación ni el request que la originó.
- Transporte: **Expo Push Service**, `POST https://exp.host/--/api/v2/push/send`.
- Baseline Alembic para `down_revision`: **`ac4f76d969b7`**.
- `seed.py` NO envía push: se queda con inserción directa de `models.Notificacion`.
- Los tests mockean la llamada HTTP a Expo (`_post_expo`) y monkeypatchean `notificaciones_service.SessionLocal` al factory de prueba para que la background task use la BD en memoria.
- Móvil: no hay harness de tests RN; la verificación móvil es que los archivos compilan con `babel-preset-expo` (`node -e` con `@babel/core` + `babel-preset-expo`, ya instalados). El demo en dispositivo real es paso manual documentado.

---

### Task 1: Modelo `DispositivoPush` + migración Alembic

**Files:**
- Modify: `api/app/models.py` (añadir clase `DispositivoPush` y relationship en `Usuario`)
- Create: `api/migrations/versions/20260715_1100_dispositivos_push.py`
- Test: `api/tests/test_push_dispositivos.py`

**Interfaces:**
- Produces: modelo `models.DispositivoPush(id, usuario_id, token, plataforma, creado_en)`; `Usuario.dispositivos_push` (relationship, back_populates="usuario").

- [ ] **Step 1: Escribir el test que falla**

Crear `api/tests/test_push_dispositivos.py`:

```python
"""Pruebas del modelo DispositivoPush (registro de tokens de push)."""
from app import models


def test_dispositivo_push_roundtrip(db_session):
    db = db_session()
    # 'miembro@demo.com' se siembra en conftest; tomamos su id
    usuario = db.query(models.Usuario).filter_by(correo="miembro@demo.com").first()
    db.add(models.DispositivoPush(
        usuario_id=usuario.id, token="ExponentPushToken[abc123]", plataforma="android",
    ))
    db.commit()

    guardado = db.query(models.DispositivoPush).filter_by(usuario_id=usuario.id).one()
    assert guardado.token == "ExponentPushToken[abc123]"
    assert guardado.plataforma == "android"
    assert guardado in usuario.dispositivos_push
    db.close()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_dispositivos.py -v`
Expected: FAIL con `AttributeError: module 'app.models' has no attribute 'DispositivoPush'`

- [ ] **Step 3: Añadir el modelo y el relationship**

En `api/app/models.py`, localizar la clase `Notificacion` (empieza en la línea ~402) y añadir DESPUÉS de ella:

```python
class DispositivoPush(Base):
    __tablename__ = "dispositivos_push"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    plataforma = Column(String(20))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="dispositivos_push")
```

En la clase `Usuario` (línea ~55), junto a las otras relationships (después de `notificaciones = relationship("Notificacion", back_populates="usuario")`, línea ~74), añadir:

```python
    dispositivos_push = relationship("DispositivoPush", back_populates="usuario")
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_dispositivos.py -v`
Expected: PASS

- [ ] **Step 5: Crear la migración Alembic**

Crear `api/migrations/versions/20260715_1100_dispositivos_push.py`:

```python
"""dispositivos push (IF-11)

Revision ID: b1d2e3f4a5c6
Revises: ac4f76d969b7
Create Date: 2026-07-15 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1d2e3f4a5c6"
down_revision: Union[str, None] = "ac4f76d969b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dispositivos_push",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("plataforma", sa.String(length=20), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("dispositivos_push")
```

- [ ] **Step 6: Verificar que Alembic reconoce la migración sin conflictos de cabeza**

Run: `cd api && ./.venv/bin/python -m alembic heads`
Expected: una sola cabeza, `b1d2e3f4a5c6 (head)`

- [ ] **Step 7: Commit**

```bash
git add api/app/models.py api/migrations/versions/20260715_1100_dispositivos_push.py api/tests/test_push_dispositivos.py
git commit -m "feat(push): modelo DispositivoPush y migración (IF-11)"
```

---

### Task 2: Servicio `notificaciones_service` (helper central + envío)

**Files:**
- Create: `api/app/notificaciones_service.py`
- Test: `api/tests/test_push_envio.py`

**Interfaces:**
- Consumes: `models.DispositivoPush`, `models.Notificacion`, `app.database.SessionLocal`.
- Produces:
  - `crear_notificacion(db: Session, usuario_id: int, titulo: str, mensaje: str, background_tasks=None) -> None` — añade la fila `Notificacion` (sin commit; lo hace el caller) y encola `enviar_push` si `background_tasks` no es None.
  - `enviar_push(usuario_id: int, titulo: str, mensaje: str) -> None` — tarea autónoma; abre su propia `SessionLocal`, envía y purga tokens inválidos. Best-effort.
  - `_post_expo(mensajes: list[dict]) -> list[dict]` — POST a Expo, devuelve la lista `data` de tickets. Punto de mock en tests.
  - `EXPO_PUSH_URL: str`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `api/tests/test_push_envio.py`:

```python
"""Pruebas del envío push (Expo mockeado) y del helper central."""
import pytest

from app import models, notificaciones_service as ns


@pytest.fixture
def usuario_con_token(db_session, monkeypatch):
    """Registra un dispositivo para 'miembro' y apunta SessionLocal a la BD de prueba."""
    # La tarea enviar_push abre su propia SessionLocal: en tests debe ser la de memoria.
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    db = db_session()
    usuario = db.query(models.Usuario).filter_by(correo="miembro@demo.com").first()
    db.add(models.DispositivoPush(usuario_id=usuario.id, token="ExponentPushToken[ok]", plataforma="ios"))
    db.commit()
    uid = usuario.id
    db.close()
    return uid


def test_enviar_push_llama_expo_con_el_token(usuario_con_token, monkeypatch):
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: (capturado.setdefault("m", mensajes), [])[1])

    ns.enviar_push(usuario_con_token, "Título", "Cuerpo")

    assert capturado["m"] == [
        {"to": "ExponentPushToken[ok]", "title": "Título", "body": "Cuerpo", "sound": "default"}
    ]


def test_enviar_push_purga_token_no_registrado(usuario_con_token, db_session, monkeypatch):
    # Expo responde que ese token ya no está registrado -> se debe borrar.
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: [
        {"status": "error", "message": "not registered",
         "details": {"error": "DeviceNotRegistered"}}
    ])

    ns.enviar_push(usuario_con_token, "T", "C")

    db = db_session()
    assert db.query(models.DispositivoPush).filter_by(usuario_id=usuario_con_token).count() == 0
    db.close()


def test_enviar_push_falla_no_lanza(usuario_con_token, monkeypatch):
    def explota(mensajes):
        raise RuntimeError("Expo caído")
    monkeypatch.setattr(ns, "_post_expo", explota)

    # No debe lanzar: best-effort.
    ns.enviar_push(usuario_con_token, "T", "C")


def test_enviar_push_sin_dispositivos_no_llama_expo(db_session, monkeypatch):
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    llamado = {"n": 0}
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: llamado.update(n=llamado["n"] + 1) or [])
    db = db_session()
    admin = db.query(models.Usuario).filter_by(correo="admin@demo.com").first()
    aid = admin.id
    db.close()

    ns.enviar_push(aid, "T", "C")

    assert llamado["n"] == 0
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_envio.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.notificaciones_service'`

- [ ] **Step 3: Escribir el servicio**

Crear `api/app/notificaciones_service.py`:

```python
"""
Creación de notificaciones y envío push (Expo).

crear_notificacion() es la ÚNICA puerta para crear una notificación (salvo el
seed): inserta la fila en BD y, si se le pasa un BackgroundTasks, encola el
envío push. El envío es best-effort: nunca rompe la acción que lo originó.
"""
import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_TIMEOUT = 10.0


def crear_notificacion(db: Session, usuario_id: int, titulo: str, mensaje: str,
                       background_tasks=None) -> None:
    db.add(models.Notificacion(usuario_id=usuario_id, titulo=titulo, mensaje=mensaje))
    if background_tasks is not None:
        background_tasks.add_task(enviar_push, usuario_id, titulo, mensaje)


def _post_expo(mensajes: list[dict]) -> list[dict]:
    """POST a la Expo Push API. Devuelve la lista 'data' de tickets."""
    with httpx.Client(timeout=_TIMEOUT) as cliente:
        respuesta = cliente.post(EXPO_PUSH_URL, json=mensajes)
        respuesta.raise_for_status()
        return respuesta.json().get("data", [])


def enviar_push(usuario_id: int, titulo: str, mensaje: str) -> None:
    """Tarea de fondo: envía el push a los dispositivos del usuario y purga
    los tokens que Expo reporte como no registrados. Best-effort."""
    db = SessionLocal()
    try:
        dispositivos = db.query(models.DispositivoPush).filter_by(usuario_id=usuario_id).all()
        if not dispositivos:
            return
        mensajes = [
            {"to": d.token, "title": titulo, "body": mensaje, "sound": "default"}
            for d in dispositivos
        ]
        try:
            tickets = _post_expo(mensajes)
        except Exception:
            return  # best-effort: no rompemos nada si Expo falla
        for disp, ticket in zip(dispositivos, tickets):
            if (ticket.get("status") == "error"
                    and ticket.get("details", {}).get("error") == "DeviceNotRegistered"):
                db.delete(disp)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_envio.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add api/app/notificaciones_service.py api/tests/test_push_envio.py
git commit -m "feat(push): servicio notificaciones_service con envío Expo best-effort"
```

---

### Task 3: Endpoints de registro/baja de dispositivo

**Files:**
- Modify: `api/app/schemas.py` (añadir `DispositivoRegistro`)
- Modify: `api/app/routers/notificaciones.py` (añadir POST y DELETE `/dispositivos`)
- Test: `api/tests/test_push_endpoints.py`

**Interfaces:**
- Consumes: `models.DispositivoPush`, `get_current_user`.
- Produces:
  - `POST /notificaciones/dispositivos` con body `{token: str, plataforma: str | None}` → 200, idempotente (reasigna el token al usuario actual si ya existía).
  - `DELETE /notificaciones/dispositivos?token=<token>` → 204.
  - Schema `DispositivoRegistro(token: str, plataforma: str | None)`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `api/tests/test_push_endpoints.py`:

```python
"""Pruebas de los endpoints de registro de dispositivos push."""


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_registrar_dispositivo(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    r = client.post("/notificaciones/dispositivos",
                    headers=h, json={"token": "ExponentPushToken[xyz]", "plataforma": "android"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_registrar_dispositivo_requiere_auth(client):
    r = client.post("/notificaciones/dispositivos", json={"token": "ExponentPushToken[xyz]"})
    assert r.status_code == 401


def test_registrar_token_repetido_es_idempotente(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    body = {"token": "ExponentPushToken[dup]", "plataforma": "ios"}
    assert client.post("/notificaciones/dispositivos", headers=h, json=body).status_code == 200
    # Segundo registro del mismo token: no duplica ni falla
    assert client.post("/notificaciones/dispositivos", headers=h, json=body).status_code == 200


def test_reasignar_token_a_otro_usuario(client):
    body = {"token": "ExponentPushToken[compartido]", "plataforma": "android"}
    h1 = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h1, json=body)
    # El mismo dispositivo ahora lo usa el entrenador
    h2 = _login(client, "entrenador@demo.com", "entrenadorpass123")
    r = client.post("/notificaciones/dispositivos", headers=h2, json=body)
    assert r.status_code == 200


def test_eliminar_dispositivo(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h,
                json={"token": "ExponentPushToken[borrar]"})
    r = client.request("DELETE", "/notificaciones/dispositivos",
                       headers=h, params={"token": "ExponentPushToken[borrar]"})
    assert r.status_code == 204
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_endpoints.py -v`
Expected: FAIL (404 en los endpoints nuevos)

- [ ] **Step 3: Añadir el schema**

En `api/app/schemas.py`, dentro de la sección `NOTIFICACIONES y PERFIL del jugador` (después de `class NotificacionOut`, línea ~516), añadir:

```python
class DispositivoRegistro(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    plataforma: str | None = Field(default=None, max_length=20)
```

- [ ] **Step 4: Añadir los endpoints**

En `api/app/routers/notificaciones.py`, actualizar los imports de la cabecera:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import NotificacionOut, DispositivoRegistro
```

Y añadir al final del archivo:

```python
# ---------------------------------------------------------------- dispositivos push
@router.post("/dispositivos")
def registrar_dispositivo(
    datos: DispositivoRegistro,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Registra (o reasigna) el token de push del dispositivo actual."""
    disp = db.query(models.DispositivoPush).filter_by(token=datos.token).first()
    if disp is None:
        disp = models.DispositivoPush(token=datos.token)
        db.add(disp)
    disp.usuario_id = usuario.id
    disp.plataforma = datos.plataforma
    db.commit()
    return {"ok": True}


@router.delete("/dispositivos", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_dispositivo(
    token: str,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Baja del token (al cerrar sesión). Solo borra si es del usuario actual."""
    disp = db.query(models.DispositivoPush).filter_by(token=token, usuario_id=usuario.id).first()
    if disp is not None:
        db.delete(disp)
        db.commit()
```

- [ ] **Step 5: Correr los tests para verificar que pasan**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_endpoints.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add api/app/schemas.py api/app/routers/notificaciones.py api/tests/test_push_endpoints.py
git commit -m "feat(push): endpoints de registro y baja de dispositivo"
```

---

### Task 4: Enganchar el push en la invitación a equipo

**Files:**
- Modify: `api/app/routers/equipos.py` (usar `crear_notificacion` + `BackgroundTasks`)
- Test: `api/tests/test_push_integracion_equipos.py`

**Interfaces:**
- Consumes: `notificaciones_service.crear_notificacion`, `fastapi.BackgroundTasks`.
- Produces: al invitar a un jugador con dispositivo registrado, se encola un push con título "Invitación a equipo".

- [ ] **Step 1: Escribir el test que falla**

Crear `api/tests/test_push_integracion_equipos.py`:

```python
"""La invitación a equipo debe encolar un push al jugador invitado."""
from app import models, notificaciones_service as ns


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_invitacion_encola_push(client, db_session, monkeypatch):
    # La tarea usa su propia SessionLocal: apuntarla a la BD de prueba.
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda m: (capturado.setdefault("m", m), [])[1])

    # 'miembro' ya está en Equipo A; usamos un jugador nuevo sin equipo.
    client.post("/auth/register", json={"nombre": "Libre", "correo": "libre@demo.com", "password": "clave12345"})
    h_jug = _login(client, "libre@demo.com", "clave12345")
    client.post("/notificaciones/dispositivos", headers=h_jug,
                json={"token": "ExponentPushToken[libre]", "plataforma": "android"})
    jid = client.get("/auth/me", headers=h_jug).json()["id"]

    # El entrenador (dueño del Equipo A, id=1) lo invita.
    h_ent = _login(client, "entrenador@demo.com", "entrenadorpass123")
    r = client.post("/equipos/1/invitaciones", headers=h_ent, json={"jugador_id": jid})
    assert r.status_code == 201

    # Se generó el push al token del jugador invitado.
    assert capturado["m"][0]["to"] == "ExponentPushToken[libre]"
    assert capturado["m"][0]["title"] == "Invitación a equipo"
    # Y la notificación quedó en BD (respaldo).
    db = db_session()
    assert db.query(models.Notificacion).filter_by(usuario_id=jid).count() == 1
    db.close()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_integracion_equipos.py -v`
Expected: FAIL en `capturado["m"]` (KeyError): hoy la invitación inserta la notificación directo, sin push.

- [ ] **Step 3: Enganchar `crear_notificacion` con BackgroundTasks**

En `api/app/routers/equipos.py`, añadir `BackgroundTasks` al import de fastapi (localizar la línea `from fastapi import ...` y añadir `BackgroundTasks`), y añadir el import del servicio junto a los demás imports de `app`:

```python
from app import notificaciones_service
```

Modificar el handler `invitar_jugador` (línea ~309). Cambiar la firma para recibir `background_tasks: BackgroundTasks` y reemplazar el `db.add(models.Notificacion(...))` por la llamada al helper:

```python
@router.post("/{equipo_id}/invitaciones", response_model=InvitacionOut, status_code=status.HTTP_201_CREATED)
def invitar_jugador(
    equipo_id: int, datos: InvitacionCrear, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user),
):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)

    jugador = db.get(models.Usuario, datos.jugador_id)
    if jugador is None or jugador.rol.nombre != "jugador":
        raise HTTPException(status_code=400, detail="El usuario no es un jugador válido")
    if _jugador_en_algun_equipo(db, jugador.id):
        raise HTTPException(status_code=409, detail="El jugador ya pertenece a un equipo")

    ya = (
        db.query(models.InvitacionEquipo)
        .filter_by(equipo_id=equipo_id, jugador_id=jugador.id, estado="pendiente")
        .first()
    )
    if ya:
        raise HTTPException(status_code=409, detail="Ya existe una invitación pendiente para este jugador")

    inv = models.InvitacionEquipo(equipo_id=equipo_id, jugador_id=jugador.id)
    db.add(inv)
    # Notificación interna + push para el jugador
    notificaciones_service.crear_notificacion(
        db, jugador.id, "Invitación a equipo",
        f"{eq.nombre} te invitó a unirte al equipo.", background_tasks,
    )
    db.commit()
    db.refresh(inv)
    return inv
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_integracion_equipos.py -v`
Expected: PASS

- [ ] **Step 5: Correr las pruebas de equipos existentes (no romper nada)**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_equipos.py tests/test_invitaciones.py -q`
Expected: PASS (todas)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/equipos.py api/tests/test_push_integracion_equipos.py
git commit -m "feat(push): invitación a equipo dispara push vía helper central"
```

---

### Task 5: Enganchar el push en los pagos

**Files:**
- Modify: `api/app/pagos_service.py` (`_notificar` delega en `crear_notificacion`; propagar `background_tasks`)
- Modify: `api/app/routers/pagos.py` (handlers reciben y pasan `BackgroundTasks`)
- Test: `api/tests/test_push_integracion_pagos.py`

**Interfaces:**
- Consumes: `notificaciones_service.crear_notificacion`, `fastapi.BackgroundTasks`.
- Produces: `pagar_reserva`, `pagar_inscripcion`, `confirmar_pago` aceptan `background_tasks` y encolan push al notificar.

- [ ] **Step 1: Escribir el test que falla**

Crear `api/tests/test_push_integracion_pagos.py`:

```python
"""Un pago de reserva confirmado debe encolar un push al pagador."""
from app import models, notificaciones_service as ns


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_pago_reserva_encola_push(client, db_session, monkeypatch):
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda m: (capturado.setdefault("m", m), [])[1])

    h = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h,
                json={"token": "ExponentPushToken[pagador]", "plataforma": "ios"})

    # Reserva sobre la Cancha 1 (precio 200, sembrada en conftest)
    reserva = client.post("/reservas", headers=h, json={
        "cancha_id": 1, "fecha": "2027-01-01", "hora_inicio": "10:00", "hora_fin": "11:00",
    }).json()

    # Pago con tarjeta (el MockGateway aprueba las tarjetas válidas)
    r = client.post(f"/pagos/reserva/{reserva['id']}", headers=h, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111111", "exp_mes": 12, "exp_anio": 2030,
                    "cvv": "123", "titular": "Miembro Uno"},
    })
    assert r.status_code == 201

    assert capturado["m"][0]["to"] == "ExponentPushToken[pagador]"
    assert capturado["m"][0]["title"] == "Pago confirmado"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_integracion_pagos.py -v`
Expected: FAIL en `capturado["m"]` (KeyError): el pago no encola push todavía.

- [ ] **Step 3: Propagar `background_tasks` en `pagos_service.py`**

En `api/app/pagos_service.py`, añadir el import del servicio junto a los demás imports de `app` (después de `from app import models`):

```python
from app import notificaciones_service
```

Reemplazar `_notificar` (línea ~40) para delegar:

```python
def _notificar(db: Session, usuario_id: int, titulo: str, mensaje: str,
               background_tasks=None) -> None:
    notificaciones_service.crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)
```

Cambiar la firma de `pagar_reserva` (línea ~62) para aceptar `background_tasks=None` y pasarlo en las dos llamadas a `_notificar`:

```python
def pagar_reserva(db: Session, usuario: models.Usuario, reserva: models.Reserva,
                  datos: PagoCreate, gateway: PaymentGateway | None = None,
                  background_tasks=None) -> models.Pago:
```

En su cuerpo, cambiar las dos llamadas `_notificar(db, usuario.id, "Pago confirmado", ...)` y `_notificar(db, usuario.id, "Pago en revisión", ...)` para añadir `background_tasks` como último argumento:

```python
        _notificar(db, usuario.id, "Pago confirmado",
                   f"Tu {concepto} quedó pagada. Folio {pago.referencia}.", background_tasks)
```
```python
        _notificar(db, usuario.id, "Pago en revisión",
                   f"Registramos tu transferencia por {concepto}. Pendiente de confirmación.", background_tasks)
```

Hacer lo mismo en `pagar_inscripcion` (línea ~95): añadir `background_tasks=None` a la firma y pasarlo en sus dos llamadas a `_notificar`.

Y en `confirmar_pago` (línea ~131): añadir `background_tasks=None` a la firma y pasarlo en su llamada a `_notificar`:

```python
def confirmar_pago(db: Session, pago: models.Pago, background_tasks=None) -> models.Pago:
```
```python
    _notificar(db, pago.usuario_id, "Pago confirmado",
               f"Tu pago ({pago.concepto}) fue confirmado. Folio {pago.referencia}.", background_tasks)
```

- [ ] **Step 4: Propagar `BackgroundTasks` en los handlers de `pagos.py`**

En `api/app/routers/pagos.py`, añadir `BackgroundTasks` al import de fastapi (línea 8):

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
```

En `pagar_reserva` (handler, línea ~24), añadir el parámetro y pasarlo al servicio:

```python
@router.post("/reserva/{reserva_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_reserva(
    reserva_id: int,
    datos: PagoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = db.get(models.Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una reserva ajena")
    return pagos_service.pagar_reserva(db, usuario, reserva, datos, background_tasks=background_tasks)
```

En `pagar_inscripcion` (handler, línea ~39), igual: añadir `background_tasks: BackgroundTasks` y pasar `background_tasks=background_tasks` a `pagos_service.pagar_inscripcion`.

En `confirmar_pago` (handler, línea ~54), añadir `background_tasks: BackgroundTasks` y pasar `background_tasks=background_tasks` a `pagos_service.confirmar_pago`:

```python
@router.post("/{pago_id}/confirmar", response_model=PagoOut)
def confirmar_pago(
    pago_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    pago = db.get(models.Pago, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    confirmado = pagos_service.confirmar_pago(db, pago, background_tasks=background_tasks)
    audit.registrar(
        audit.PAGO_CONFIRMADO, actor_id=_admin.id, objetivo=pago.id,
        detalle=f"monto={pago.monto} metodo={pago.metodo}",
    )
    return confirmado
```

- [ ] **Step 5: Correr el test nuevo y toda la suite de pagos**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_push_integracion_pagos.py tests/test_pagos.py tests/test_pagos_inscripcion.py tests/test_pagos_transferencia.py -q`
Expected: PASS (todas)

- [ ] **Step 6: Commit**

```bash
git add api/app/pagos_service.py api/app/routers/pagos.py api/tests/test_push_integracion_pagos.py
git commit -m "feat(push): pagos disparan push vía helper central con BackgroundTasks"
```

---

### Task 6: Módulo móvil `push.js`

**Files:**
- Create: `mobile/src/push.js`
- Modify: `mobile/package.json` (dependencias, vía `npx expo install`)

**Interfaces:**
- Consumes: `apiPost`, `apiDelete` de `./api`; `Constants.expoConfig.extra.eas.projectId`.
- Produces:
  - `registrarParaPush(): Promise<void>` — pide permisos, obtiene el Expo token y lo registra vía API.
  - `desregistrar(): Promise<void>` — da de baja el token local.
  - `configurarManejadores(navigationRef): () => void` — monta el listener de tap (navega a "Avisos"); devuelve función de limpieza.

- [ ] **Step 1: Instalar dependencias**

Run: `cd mobile && npx expo install expo-notifications expo-device`
Expected: `package.json` gana `expo-notifications` (~0.28.x) y `expo-device` (~6.0.x) compatibles con SDK 51.

- [ ] **Step 2: Escribir el módulo**

Crear `mobile/src/push.js`:

```javascript
// Notificaciones push (Expo). El backend envía vía Expo Push Service; aquí
// pedimos permiso, registramos el token del dispositivo y manejamos la llegada.
import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { apiPost, apiDelete } from "./api";

// Mostrar la notificación aunque la app esté en primer plano.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let _tokenActual = null;

// Pide permiso, obtiene el Expo push token y lo registra en la API.
export async function registrarParaPush() {
  if (!Device.isDevice) return; // los push remotos no funcionan en emulador
  try {
    const { status: previo } = await Notifications.getPermissionsAsync();
    let status = previo;
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return;

    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    if (!projectId) return; // sin projectId de EAS no se puede obtener token

    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
    _tokenActual = token;
    await apiPost("/notificaciones/dispositivos", { token, plataforma: Platform.OS });
  } catch (_) {
    // best-effort: si falla el registro, la app sigue funcionando
  }
}

// Da de baja el token al cerrar sesión.
export async function desregistrar() {
  if (!_tokenActual) return;
  try {
    await apiDelete(`/notificaciones/dispositivos?token=${encodeURIComponent(_tokenActual)}`);
  } catch (_) {
    // ignorar
  } finally {
    _tokenActual = null;
  }
}

// Al tocar una notificación, abre la pantalla de Avisos. Devuelve limpieza.
export function configurarManejadores(navigationRef) {
  const sub = Notifications.addNotificationResponseReceivedListener(() => {
    if (navigationRef?.isReady?.()) {
      navigationRef.navigate("Avisos");
    }
  });
  return () => sub.remove();
}
```

- [ ] **Step 3: Verificar que compila con babel-preset-expo**

Run:
```bash
cd mobile && node -e '
const babel = require("@babel/core");
babel.transformFileSync("src/push.js", {presets:["babel-preset-expo"]});
console.log("OK push.js");
'
```
Expected: `OK push.js`

- [ ] **Step 4: Commit**

```bash
git add mobile/src/push.js mobile/package.json mobile/package-lock.json
git commit -m "feat(push): módulo móvil push.js (registro, baja, manejadores)"
```

---

### Task 7: Integración móvil (auth, raíz, config EAS)

**Files:**
- Modify: `mobile/src/auth.js` (registrar/desregistrar en login/logout/arranque)
- Modify: `mobile/App.js` (ref de navegación + montar manejadores)
- Modify: `mobile/app.json` (placeholder `extra.eas.projectId` + config de notificaciones)

**Interfaces:**
- Consumes: `registrarParaPush`, `desregistrar`, `configurarManejadores` de `./src/push`.
- Produces: la app registra el token tras login y en arranque con sesión, lo da de baja en logout, y navega a "Avisos" al tocar un push.

**Nota sobre la pantalla destino:** el listener navega a la ruta `"Avisos"`. Verificar en `App.js` el `name` real de la pestaña/pantalla de `NotificationsScreen` y usar ese literal si difiere de `"Avisos"`.

- [ ] **Step 1: Registrar/desregistrar en `auth.js`**

En `mobile/src/auth.js`, añadir el import tras los imports existentes:

```javascript
import { registrarParaPush, desregistrar } from "./push";
```

En el `useEffect` de arranque, tras `setUsuario(me);` (línea ~18), añadir el registro best-effort:

```javascript
          setUsuario(me);
          registrarParaPush();
```

En `login()`, tras `setUsuario(me);` (línea ~32), añadir:

```javascript
    setUsuario(me);
    registrarParaPush();
```

En `logout()` (línea ~42), dar de baja el token ANTES de borrar el token de sesión (el `apiDelete` necesita el auth aún válido):

```javascript
  async function logout() {
    await desregistrar();
    await borrarToken();
    setUsuario(null);
  }
```

- [ ] **Step 2: Montar los manejadores en `App.js`**

En `mobile/App.js`, actualizar el import de navegación para incluir la ref:

```javascript
import { NavigationContainer, DefaultTheme, useNavigation, createNavigationContainerRef } from "@react-navigation/native";
```

Añadir el import de push y `useEffect`/`useRef` de React. Localizar `import React from "react";` y cambiarlo a:

```javascript
import React, { useEffect } from "react";
```

Añadir tras los imports de pantallas:

```javascript
import { configurarManejadores } from "./src/push";

const navigationRef = createNavigationContainerRef();
```

Localizar el `<NavigationContainer` (buscar `NavigationContainer` en el JSX) y añadirle la prop `ref={navigationRef}`. En el componente que lo renderiza, añadir un `useEffect` que monte los manejadores una vez:

```javascript
  useEffect(() => {
    const limpiar = configurarManejadores(navigationRef);
    return limpiar;
  }, []);
```

- [ ] **Step 3: Añadir el placeholder de EAS y config de notificaciones en `app.json`**

En `mobile/app.json`, dentro de `expo.extra`, añadir el bloque `eas` (dejando el `apiUrl` existente):

```json
    "extra": {
      "//": "Solo se usa en builds de produccion: en desarrollo la IP se deduce del host de Expo.",
      "//2": "Desde un telefono fisico NO sirve 'localhost'. Usa la IP local de tu PC.",
      "apiUrl": "http://10.133.61.227:8000",
      "eas": {
        "//": "RELLENAR con el projectId de tu proyecto EAS antes del build. Sin esto, el push no obtiene token.",
        "projectId": ""
      }
    }
```

Y dentro de `expo`, añadir el plugin de notificaciones (junto a las demás claves, p. ej. tras `"android"`):

```json
    "plugins": ["expo-notifications"],
```

- [ ] **Step 4: Verificar que los archivos móviles compilan**

Run:
```bash
cd mobile && node -e '
const babel = require("@babel/core");
for (const f of ["src/auth.js","App.js"]) babel.transformFileSync(f, {presets:["babel-preset-expo"]});
console.log("OK auth.js + App.js");
'
```
Expected: `OK auth.js + App.js`

- [ ] **Step 5: Validar que `app.json` es JSON válido**

Run: `cd mobile && node -e 'JSON.parse(require("fs").readFileSync("app.json","utf8")); console.log("app.json OK")'`
Expected: `app.json OK`

- [ ] **Step 6: Commit**

```bash
git add mobile/src/auth.js mobile/App.js mobile/app.json
git commit -m "feat(push): integración móvil (auth, manejadores, config EAS)"
```

---

### Task 8: Verificación final y documentación del demo

**Files:**
- Modify: `docs/DESPLIEGUE.md` (o crear `docs/PUSH.md`) con el paso manual de demo en dispositivo.

- [ ] **Step 1: Correr toda la suite backend**

Run: `cd api && ./.venv/bin/python -m pytest -q`
Expected: PASS (los ~197 previos + los nuevos de push).

- [ ] **Step 2: Documentar el demo en dispositivo real**

Crear `docs/PUSH.md`:

```markdown
# Notificaciones push (IF-11) — demo en dispositivo real

El backend y el móvil quedan listos. Para probar el push físico (Expo Go SDK 53+
ya no soporta push remoto), se necesita un **development build** con EAS:

1. Crear un proyecto EAS: `cd mobile && npx eas init` (genera el `projectId`).
2. Pegar ese `projectId` en `mobile/app.json` → `expo.extra.eas.projectId`.
3. Build de desarrollo: `npx eas build --profile development --platform android`.
4. Instalar el build en un teléfono físico e iniciar sesión: al conceder permiso,
   el token se registra vía `POST /notificaciones/dispositivos`.
5. Disparar un evento (invitar al jugador a un equipo, o confirmar un pago suyo):
   el teléfono recibe el push. La notificación también queda en la pantalla de
   Avisos (respaldo por polling).

El envío se hace best-effort desde `api/app/notificaciones_service.py`; los tokens
que Expo reporte como `DeviceNotRegistered` se purgan solos.
```

- [ ] **Step 3: Commit**

```bash
git add docs/PUSH.md
git commit -m "docs(push): pasos de demo en dispositivo real (IF-11)"
```

---

## Notas de ejecución

- Toda la lógica push del backend es best-effort: si Task 6/7 (móvil) se posponen, el backend (Tasks 1-5) queda funcional y probado por su cuenta.
- El literal de ruta `"Avisos"` en `push.js` debe coincidir con el `name` real de la pantalla de notificaciones en `App.js` (verificar en Task 7, Step 2).
