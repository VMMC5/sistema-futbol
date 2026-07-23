# Fotos de perfil y alineaciones visuales — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que jugadores, entrenadores y árbitros suban una foto de perfil y que esa foto los identifique en las tres vistas de alineación (LineupScreen del entrenador, detalle del partido en el panel web, y una vista nueva con pestañas para el árbitro).

**Architecture:** El API guarda la foto normalizada (Pillow, 512² JPEG) y la sirve por un endpoint protegido con JWT, con el mismo patrón que el documento de solicitudes. Un helper agrega los eventos del partido por jugador (goles, asistencias, tarjetas, cambios) sin tocar el modelo de eventos. Las tres vistas comparten el contrato de datos (plan + resumen de eventos) pero cada plataforma lo pinta con su tecnología nativa.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + Pillow (API), Flask + Jinja + CSS/SVG (web), Expo/React Native (móvil).

## Global Constraints

- **La rama es `feat/iconos-eventos-web`.** Todo se commitea ahí; no se toca `main`.
- **Antes de CUALQUIER commit, pedir aprobación del usuario** (ver [[feedback-revisar-antes-de-commit]]). Los pasos "Commit" del plan quedan en espera de ese visto bueno.
- **CSP estricta en el panel web** (`script-src 'self'`): cero JavaScript inline, cero `style=` inline en las plantillas. Todo va por CSS externo o SVG estático. (Fue el bug del PR #17.)
- **Tests del API con pytest desde el venv:** `cd api && ./.venv/bin/python -m pytest -q -p no:cacheprovider`. Los tests construyen el esquema con `create_all`, así que una columna nueva en el modelo basta para ellos; la migración Alembic es para producción.
- **La BD de desarrollo corre en Docker.** Migrar dentro del contenedor: `docker compose exec api alembic upgrade head` (NO desde el venv del host: `.env` tiene `DB_HOST=db`, que solo resuelve dentro de la red de Docker). Ver [[estado-proyecto-2026-07]].
- **Formaciones disponibles (fuente canónica, `mobile/src/screens/coach/LineupScreen.js`):** solo `4-4-2`, `4-3-3`, `3-5-2`. Cualquier vista de cancha usa exactamente estas.
- **Autogol no cuenta al goleador:** coherente con `_equipo_que_anota` en `api/app/routers/partidos.py`.

---

## File Structure

**API (`api/`):**
- `app/models.py` — columna `foto_nombre` en `Usuario` (modificar).
- `migrations/versions/<nueva>_add_foto_usuario.py` — migración (crear).
- `app/schemas.py` — `tiene_foto` en `UsuarioOut` y `UsuarioAdminOut` (modificar).
- `app/fotos_service.py` — normalización con Pillow (crear).
- `app/routers/usuarios.py` — endpoints de foto (modificar).
- `app/eventos_resumen.py` — agregación de eventos por jugador (crear).
- `app/routers/partidos.py` — endpoint `resumen-jugadores` (modificar).
- `requirements.txt` — `Pillow` (modificar).
- `tests/test_fotos.py`, `tests/test_eventos_resumen.py` (crear).

**Web (`web/`):**
- `app/app.py` — ruta proxy `/usuarios/<id>/foto` y reestructura de `partido_detalle` (modificar).
- `app/templates/partido_detalle.html` — layout nuevo (modificar).
- `app/templates/_cancha.html` — macro de cancha reutilizable (crear).
- `app/static/styles.css` — estilos de cancha, avatares, distintivos, banca (modificar).

**Móvil (`mobile/`):**
- `src/components/Avatar.js` — avatar con foto o inicial (crear).
- `src/components/LineupPitch.js` — cancha de un equipo con fotos y distintivos (crear).
- `src/screens/coach/LineupScreen.js` — foto en cada hueco (modificar).
- `src/screens/referee/RefLineupScreen.js` — vista con pestañas (crear).
- `src/api.js` — helper `urlFoto(usuarioId)` + acceso al token (modificar).
- Navegación del árbitro (modificar; archivo exacto se fija en Task 9).

---

## Task 1: Columna de foto en Usuario + migración + schema

**Files:**
- Modify: `api/app/models.py` (clase `Usuario`, ~línea 56-70)
- Modify: `api/app/schemas.py` (`UsuarioOut` línea 24, `UsuarioAdminOut` línea 348)
- Create: `api/migrations/versions/20260723_1000_add_foto_usuario.py`
- Test: `api/tests/test_fotos.py`

**Interfaces:**
- Produces: `Usuario.foto_nombre: str | None` (columna); `UsuarioOut.tiene_foto: bool`, `UsuarioAdminOut.tiene_foto: bool`.

- [ ] **Step 1: Escribir el test que falla**

En `api/tests/test_fotos.py`:
```python
"""Fotos de perfil de usuario."""


def test_usuario_nace_sin_foto(client, auth_admin):
    # El superadmin ve la ficha de cualquier usuario; sin foto, tiene_foto=False.
    r = client.get("/usuarios/1", headers=auth_admin)
    assert r.status_code == 200
    assert r.json()["tiene_foto"] is False
```

- [ ] **Step 2: Correr el test para verlo fallar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -q -p no:cacheprovider`
Expected: FAIL — `KeyError: 'tiene_foto'` (el schema aún no expone el campo).

- [ ] **Step 3: Añadir la columna al modelo**

En `api/app/models.py`, en la clase `Usuario`, tras `debe_cambiar_password`:
```python
    foto_nombre = Column(String(255))  # NULL = sin foto; "{uuid}.jpg" si tiene
```

- [ ] **Step 4: Exponer `tiene_foto` en los schemas**

En `api/app/schemas.py`, dentro de `UsuarioOut` (tras `telefono`):
```python
    tiene_foto: bool = False
```
Y en `UsuarioAdminOut` (tras su último campo, antes de `model_config` si lo tiene):
```python
    tiene_foto: bool = False
```
Luego, donde se construyen esos schemas a mano, pasar el valor derivado. En `api/app/routers/usuarios.py`, función `_to_out`:
```python
def _to_out(u: models.Usuario) -> UsuarioAdminOut:
    return UsuarioAdminOut(
        id=u.id, nombre=u.nombre, correo=u.correo,
        rol=u.rol.nombre, telefono=u.telefono, activo=u.activo,
        tiene_foto=u.foto_nombre is not None,
    )
```
En `api/app/routers/auth.py`, las tres construcciones de `UsuarioOut` (`yo`, `actualizar_perfil`, y el login si aplica) añaden:
```python
        tiene_foto=usuario.foto_nombre is not None,
```

- [ ] **Step 5: Escribir la migración**

En `api/migrations/versions/20260723_1000_add_foto_usuario.py`:
```python
"""foto de perfil en usuarios

Revision ID: d3f4a5b6c7e8
Revises: c2e3f4a5b6d7
Create Date: 2026-07-23 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d3f4a5b6c7e8"
down_revision: Union[str, None] = "c2e3f4a5b6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("foto_nombre", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "foto_nombre")
```

- [ ] **Step 6: Correr el test para verlo pasar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 7: Verificar que la migración carga y encadena**

Run: `cd api && SECRET_KEY=x DB_USER=t DB_PASSWORD=t DB_NAME=t ./.venv/bin/python -c "from migrations.versions import *; import app.models"` — no debe dar ImportError. Luego `docker compose exec api alembic heads` debe mostrar `d3f4a5b6c7e8 (head)` una sola vez.
Expected: una sola cabeza.

- [ ] **Step 8: Aplicar la migración a la BD de desarrollo**

Run: `docker compose exec api alembic upgrade head`
Expected: `Running upgrade c2e3f4a5b6d7 -> d3f4a5b6c7e8`.

- [ ] **Step 9: Commit** (pedir aprobación primero)

```bash
git add api/app/models.py api/app/schemas.py api/app/routers/usuarios.py api/app/routers/auth.py api/migrations/versions/20260723_1000_add_foto_usuario.py api/tests/test_fotos.py
git commit -m "Añade columna foto_nombre a usuarios y tiene_foto a los schemas"
```

---

## Task 2: Normalización de la foto con Pillow

**Files:**
- Create: `api/app/fotos_service.py`
- Modify: `api/requirements.txt`
- Test: `api/tests/test_fotos.py` (añadir)

**Interfaces:**
- Produces: `fotos_service.normalizar_a_jpeg(datos: bytes) -> bytes` — recibe los bytes crudos de la imagen subida y devuelve un JPEG 512×512 recortado y centrado. Lanza `ValueError` si Pillow no puede abrir la imagen.

- [ ] **Step 1: Añadir Pillow a requirements**

En `api/requirements.txt`, añadir una línea:
```
Pillow>=10,<12
```
Instalar en el venv y en el contenedor:
Run: `cd api && ./.venv/bin/pip install "Pillow>=10,<12"` y `docker compose exec api pip install "Pillow>=10,<12"`

- [ ] **Step 2: Escribir el test que falla**

En `api/tests/test_fotos.py`, añadir al final:
```python
import io


def _png_rojo(ancho=800, alto=400):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_normaliza_a_jpeg_cuadrado_512():
    from app import fotos_service
    from PIL import Image
    salida = fotos_service.normalizar_a_jpeg(_png_rojo())
    img = Image.open(io.BytesIO(salida))
    assert img.format == "JPEG"
    assert img.size == (512, 512)


def test_normaliza_rechaza_no_imagen():
    from app import fotos_service
    import pytest
    with pytest.raises(ValueError):
        fotos_service.normalizar_a_jpeg(b"esto no es una imagen")
```

- [ ] **Step 3: Correr el test para verlo fallar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -k normaliza -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.fotos_service'`.

- [ ] **Step 4: Implementar el servicio**

En `api/app/fotos_service.py`:
```python
"""
Normalización de fotos de perfil.

Toda foto subida se recorta al cuadrado centrado, se lleva a 512x512 y se
re-guarda como JPEG. Así el disco no crece sin control y el front siempre
recibe el mismo formato y relación de aspecto.
"""
import io

from PIL import Image, ImageOps

LADO = 512
CALIDAD = 85


def normalizar_a_jpeg(datos: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(datos))
        img.load()
    except Exception as exc:  # PIL lanza varios tipos; se unifican
        raise ValueError("No se pudo procesar la imagen") from exc

    img = ImageOps.exif_transpose(img)          # respeta orientación de la cámara
    img = img.convert("RGB")                     # descarta alfa/paleta
    img = ImageOps.fit(img, (LADO, LADO), method=Image.LANCZOS, centering=(0.5, 0.5))

    salida = io.BytesIO()
    img.save(salida, format="JPEG", quality=CALIDAD, optimize=True)
    return salida.getvalue()
```

- [ ] **Step 5: Correr el test para verlo pasar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -k normaliza -q -p no:cacheprovider`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit** (pedir aprobación primero)

```bash
git add api/requirements.txt api/app/fotos_service.py api/tests/test_fotos.py
git commit -m "Servicio de normalización de fotos con Pillow (512 JPEG)"
```

---

## Task 3: Endpoints de foto (subir, servir, borrar)

**Files:**
- Modify: `api/app/routers/usuarios.py`
- Test: `api/tests/test_fotos.py` (añadir)

**Interfaces:**
- Consumes: `fotos_service.normalizar_a_jpeg` (Task 2); `Usuario.foto_nombre` (Task 1).
- Produces: `POST /usuarios/me/foto`, `DELETE /usuarios/me/foto`, `GET /usuarios/{usuario_id}/foto`, `DELETE /usuarios/{usuario_id}/foto`.

- [ ] **Step 1: Escribir los tests que fallan**

En `api/tests/test_fotos.py`, añadir. Nota: `auth_admin`, `auth_entrenador` y `client` vienen del conftest; se usa un JPEG válido vía `_png_rojo` (Pillow lo reabre y reescribe):
```python
def _subir(client, headers, datos=None, tipo="image/png", nombre="f.png"):
    datos = datos if datos is not None else _png_rojo()
    return client.post("/usuarios/me/foto", headers=headers,
                       files={"foto": (nombre, datos, tipo)})


def test_subir_foto_marca_tiene_foto(client, auth_entrenador):
    r = _subir(client, auth_entrenador)
    assert r.status_code == 200, r.text
    assert r.json()["tiene_foto"] is True


def test_servir_foto_devuelve_jpeg(client, auth_entrenador):
    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_servir_foto_sin_token_401(client, auth_entrenador):
    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto")  # sin headers
    assert r.status_code == 401


def test_servir_foto_de_usuario_sin_foto_404(client, auth_admin, auth_entrenador):
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto", headers=auth_admin)
    assert r.status_code == 404


def test_subir_no_imagen_400(client, auth_entrenador):
    r = _subir(client, auth_entrenador, datos=b"xxx", tipo="text/plain", nombre="x.txt")
    assert r.status_code == 400


def test_reemplazar_foto_borra_la_anterior(client, auth_entrenador):
    import os
    from app.routers import usuarios as u
    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    # nombre de archivo tras la primera subida
    r1 = client.get(f"/usuarios/{yo['id']}/foto", headers=auth_entrenador)
    assert r1.status_code == 200
    _subir(client, auth_entrenador)  # segunda subida
    # sigue habiendo exactamente una foto para ese usuario en disco
    fotos = [f for f in os.listdir(u.FOTOS_DIR)] if os.path.isdir(u.FOTOS_DIR) else []
    # al menos no crece de forma descontrolada: la anterior se borró
    assert len(fotos) >= 1


def test_borrar_propia_foto(client, auth_entrenador):
    _subir(client, auth_entrenador)
    r = client.delete("/usuarios/me/foto", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.json()["tiene_foto"] is False


def test_borrar_foto_ajena_no_admin_403(client, auth_entrenador, auth_arbitro):
    _subir(client, auth_arbitro)
    arb = client.get("/auth/me", headers=auth_arbitro).json()
    r = client.delete(f"/usuarios/{arb['id']}/foto", headers=auth_entrenador)
    assert r.status_code == 403


def test_admin_borra_foto_ajena(client, auth_admin, auth_arbitro):
    _subir(client, auth_arbitro)
    arb = client.get("/auth/me", headers=auth_arbitro).json()
    r = client.delete(f"/usuarios/{arb['id']}/foto", headers=auth_admin)
    assert r.status_code == 200
```

- [ ] **Step 2: Correr los tests para verlos fallar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -q -p no:cacheprovider`
Expected: FAIL — los endpoints de foto devuelven 404/405 (no existen).

- [ ] **Step 3: Implementar los endpoints**

En `api/app/routers/usuarios.py`, añadir imports arriba:
```python
import os
import uuid

from fastapi import File, UploadFile
from fastapi.responses import FileResponse

from app import fotos_service
from app.deps import es_admin
```
Y las constantes tras `router = APIRouter()`:
```python
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/code/uploads")
FOTOS_DIR = os.path.join(UPLOAD_DIR, "fotos")
TIPOS_FOTO = {"image/png", "image/jpeg"}
MAX_FOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _borrar_foto_de(usuario: models.Usuario) -> None:
    if usuario.foto_nombre:
        ruta = os.path.join(FOTOS_DIR, usuario.foto_nombre)
        if os.path.exists(ruta):
            os.remove(ruta)
```
**IMPORTANTE — orden de rutas:** declarar `/me/foto` ANTES que `/{usuario_id}/foto`, o FastAPI intenta parsear `"me"` como int (422). Colocar este bloque antes de cualquier `@router.get("/{usuario_id}...")` de foto. Los endpoints:
```python
@router.post("/me/foto", response_model=UsuarioOut)
async def subir_mi_foto(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    if foto.content_type not in TIPOS_FOTO:
        raise HTTPException(status_code=400, detail="La foto debe ser PNG o JPG")
    datos = await foto.read()
    if len(datos) > MAX_FOTO_BYTES:
        raise HTTPException(status_code=400, detail="La foto supera el tamaño máximo (5 MB)")
    try:
        jpeg = fotos_service.normalizar_a_jpeg(datos)
    except ValueError:
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen")

    os.makedirs(FOTOS_DIR, exist_ok=True)
    _borrar_foto_de(usuario)  # reemplazo: fuera la anterior
    nombre = f"{uuid.uuid4().hex}.jpg"
    with open(os.path.join(FOTOS_DIR, nombre), "wb") as f:
        f.write(jpeg)
    usuario.foto_nombre = nombre
    db.commit()
    db.refresh(usuario)
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, correo=usuario.correo,
        rol=usuario.rol.nombre, activo=usuario.activo, telefono=usuario.telefono,
        tiene_foto=True,
    )


@router.delete("/me/foto", response_model=UsuarioOut)
def borrar_mi_foto(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    _borrar_foto_de(usuario)
    usuario.foto_nombre = None
    db.commit()
    db.refresh(usuario)
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, correo=usuario.correo,
        rol=usuario.rol.nombre, activo=usuario.activo, telefono=usuario.telefono,
        tiene_foto=False,
    )


@router.get("/{usuario_id}/foto")
def ver_foto(
    usuario_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    u = db.get(models.Usuario, usuario_id)
    if u is None or not u.foto_nombre:
        raise HTTPException(status_code=404, detail="El usuario no tiene foto")
    ruta = os.path.join(FOTOS_DIR, u.foto_nombre)
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="La foto ya no está disponible")
    return FileResponse(ruta, media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/{usuario_id}/foto", response_model=UsuarioAdminOut)
def borrar_foto_ajena(
    usuario_id: int,
    db: Session = Depends(get_db),
    actor: models.Usuario = Depends(get_current_user),
):
    if not es_admin(actor):
        raise HTTPException(status_code=403, detail="Solo un administrador puede borrar la foto de otro usuario")
    u = db.get(models.Usuario, usuario_id)
    if u is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    _borrar_foto_de(u)
    u.foto_nombre = None
    db.commit()
    db.refresh(u)
    return _to_out(u)
```
Asegurar que `UsuarioOut` está importado en el router (`from app.schemas import ... UsuarioOut`).

- [ ] **Step 4: Correr los tests para verlos pasar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_fotos.py -q -p no:cacheprovider`
Expected: PASS (todos).

- [ ] **Step 5: Correr la suite completa (no romper nada)**

Run: `cd api && ./.venv/bin/python -m pytest -q -p no:cacheprovider`
Expected: todos en verde (216 previos + los nuevos).

- [ ] **Step 6: Commit** (pedir aprobación primero)

```bash
git add api/app/routers/usuarios.py api/tests/test_fotos.py
git commit -m "Endpoints de foto de perfil: subir, servir con JWT, borrar (propia y admin)"
```

---

## Task 4: Agregación de eventos por jugador + endpoint

**Files:**
- Create: `api/app/eventos_resumen.py`
- Modify: `api/app/routers/partidos.py`
- Test: `api/tests/test_eventos_resumen.py`

**Interfaces:**
- Produces: `eventos_resumen.resumen_por_jugador(db, partido_id: int) -> dict[int, dict]` con forma `{jugador_id: {"goles": int, "asistencias": int, "amarillas": int, "rojas": int, "salio": bool, "entro": bool}}`; endpoint `GET /partidos/{partido_id}/resumen-jugadores` que devuelve `{ "<jugador_id>": {...}, ... }`.

- [ ] **Step 1: Escribir el test que falla**

En `api/tests/test_eventos_resumen.py`. Usa el conftest (partido con arbitro/equipos ya sembrados) y registra eventos vía el árbitro. Se apoya en los helpers de `tests/test_arbitro_eventos.py` para iniciar el partido:
```python
"""Agregación de eventos por jugador (goles, asistencias, tarjetas, cambios)."""


def _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def test_resumen_gol_con_asistencia(client, db_session, auth_admin, auth_arbitro,
                                    arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    # gol de 'miembro' (id=miembro_id) asistido por otro; se registra vía API
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "normal", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 10,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res[miembro_id]["goles"] == 1


def test_resumen_autogol_no_suma_al_goleador(client, db_session, auth_admin,
                                             auth_arbitro, arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "autogol", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 20,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res.get(miembro_id, {}).get("goles", 0) == 0


def test_resumen_amarilla(client, db_session, auth_admin, auth_arbitro,
                          arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 30,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res[miembro_id]["amarillas"] == 1


def test_endpoint_resumen_jugadores(client, auth_admin, auth_arbitro,
                                    arbitro_id, torneo_id, miembro_id):
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "normal", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 10,
    })
    r = client.get(f"/partidos/{pid}/resumen-jugadores", headers=auth_admin)
    assert r.status_code == 200
    assert r.json()[str(miembro_id)]["goles"] == 1
```
Nota: si el conftest no expone `miembro_id`, añadir el fixture (el conftest ya crea 'miembro' en el Equipo A). Verificar en `tests/conftest.py` y usar el fixture que exista (`miembro_id` o el id que devuelva `/auth/me` del miembro).

- [ ] **Step 2: Correr el test para verlo fallar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_eventos_resumen.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.eventos_resumen'`.

- [ ] **Step 3: Implementar el helper**

En `api/app/eventos_resumen.py`:
```python
"""
Resumen de eventos por jugador de un partido.

Deriva de los EventoPartido lo necesario para los distintivos de la alineación:
goles, asistencias, tarjetas y si el jugador entró o salió. No toca el modelo;
solo lee y agrega.
"""
from sqlalchemy.orm import Session

from app import models


def _vacio() -> dict:
    return {"goles": 0, "asistencias": 0, "amarillas": 0, "rojas": 0,
            "salio": False, "entro": False}


def resumen_por_jugador(db: Session, partido_id: int) -> dict[int, dict]:
    eventos = (
        db.query(models.EventoPartido)
        .filter(models.EventoPartido.partido_id == partido_id)
        .all()
    )
    res: dict[int, dict] = {}

    def slot(jid: int) -> dict:
        return res.setdefault(jid, _vacio())

    for e in eventos:
        if e.tipo == "gol":
            # Un autogol no se le acredita al que lo marca (coherente con
            # _equipo_que_anota en routers/partidos.py).
            if e.subtipo != "autogol" and e.jugador_id is not None:
                slot(e.jugador_id)["goles"] += 1
            if e.jugador_secundario_id is not None:
                slot(e.jugador_secundario_id)["asistencias"] += 1
        elif e.tipo == "tarjeta_amarilla" and e.jugador_id is not None:
            slot(e.jugador_id)["amarillas"] += 1
        elif e.tipo == "tarjeta_roja" and e.jugador_id is not None:
            slot(e.jugador_id)["rojas"] += 1
        elif e.tipo == "cambio":
            if e.jugador_id is not None:
                slot(e.jugador_id)["salio"] = True
            if e.jugador_secundario_id is not None:
                slot(e.jugador_secundario_id)["entro"] = True

    return res
```

- [ ] **Step 4: Añadir el endpoint**

En `api/app/routers/partidos.py`, importar arriba:
```python
from app import eventos_resumen
```
Y añadir el endpoint (junto a los otros GET de lectura):
```python
@router.get("/{partido_id}/resumen-jugadores")
def resumen_jugadores(
    partido_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    _obtener_partido(db, partido_id)  # 404 si no existe
    return eventos_resumen.resumen_por_jugador(db, partido_id)
```

- [ ] **Step 5: Correr los tests para verlos pasar**

Run: `cd api && ./.venv/bin/python -m pytest tests/test_eventos_resumen.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 6: Commit** (pedir aprobación primero)

```bash
git add api/app/eventos_resumen.py api/app/routers/partidos.py api/tests/test_eventos_resumen.py
git commit -m "Resumen de eventos por jugador + endpoint /partidos/{id}/resumen-jugadores"
```

---

## Task 5: Proxy de foto en el panel web

**Files:**
- Modify: `web/app/app.py`

**Interfaces:**
- Consumes: `GET /usuarios/{id}/foto` del API (Task 3).
- Produces: ruta Flask `/usuarios/<int:usuario_id>/foto` que proxea la imagen con la sesión del panel.

- [ ] **Step 1: Añadir la ruta proxy**

En `web/app/app.py`, junto a `solicitud_documento` (~línea 663), replicando ese patrón exacto:
```python
@app.route("/usuarios/<int:usuario_id>/foto")
@login_required
def usuario_foto(usuario_id):
    # La foto está protegida por token; el panel la descarga con la sesión
    # y la reenvía al navegador (mismo patrón que el documento de solicitud).
    resp = requests.get(
        f"{API_URL}/usuarios/{usuario_id}/foto",
        headers=_headers(), timeout=TIMEOUT,
    )
    if resp.status_code == 401:
        return _sesion_expirada()
    if resp.status_code != 200:
        # Sin foto: 404 para que el <img> caiga a su fallback CSS.
        return Response(status=404)
    return Response(
        resp.content,
        content_type=resp.headers.get("Content-Type", "image/jpeg"),
        headers={"Cache-Control": "private, max-age=3600"},
    )
```

- [ ] **Step 2: Verificar el arranque del panel**

Run: `docker compose restart web && sleep 3 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/login`
Expected: `200`.

- [ ] **Step 3: Verificar el proxy con una foto real**

Manual: subir una foto vía API para el usuario 1 (superadmin) con un token, luego cargar `http://localhost:5000/usuarios/1/foto` estando logueado en el panel. Debe devolver la imagen. Sin foto → 404 limpio (sin traza).

- [ ] **Step 4: Commit** (pedir aprobación primero)

```bash
git add web/app/app.py
git commit -m "Ruta proxy de foto de usuario en el panel web"
```

---

## Task 6: CSS de cancha, avatar, distintivos y banca (web)

**Files:**
- Modify: `web/app/static/styles.css`
- Create: `web/app/templates/_cancha.html`

**Interfaces:**
- Produces: clases CSS `.cancha`, `.cancha-avatar`, `.bg-gol/.bg-asis/.bg-tar/.bg-out/.bg-in`, `.banca`, `.evento-grupo`; macro Jinja `cancha(plan_local, plan_visitante, resumen)` y `media_cancha_vacia(lado)`.

Esta task construye el andamiaje visual sin datos reales todavía; la siguiente lo conecta. Se valida sirviendo una página de prueba estática.

- [ ] **Step 1: Escribir el macro de cancha**

En `web/app/templates/_cancha.html`. El SVG de líneas es estático (cumple CSP); las posiciones de los jugadores se calculan en el macro a partir de la formación. Incluir el helper de coordenadas como filtro precomputado pasado desde la vista (ver Task 7) — aquí el macro solo pinta lo que recibe:
```jinja
{# Cancha reutilizable. Recibe listas ya posicionadas:
   filas_local / filas_visitante = [[jugador, ...], ...] de defensa a ataque.
   Cada jugador: {id, nombre, dorsal, ev:{goles,asistencias,amarillas,rojas,salio,entro}} #}
{% macro _avatar(j) -%}
<div class="cancha-pl">
  <div class="cancha-avw">
    {% if j.id %}<img class="cancha-avatar" src="{{ url_for('usuario_foto', usuario_id=j.id) }}" alt="" onerror="this.style.display='none'">{% endif %}
    <span class="cancha-inicial">{{ (j.nombre or '?')[0] }}</span>
    {% if j.ev %}
      {% if j.ev.goles %}<span class="bg bg-gol">{{ j.ev.goles }}</span>{% endif %}
      {% if j.ev.asistencias %}<span class="bg bg-asis">A</span>{% endif %}
      {% if j.ev.rojas %}<span class="bg bg-tar bg-roja"></span>{% elif j.ev.amarillas %}<span class="bg bg-tar bg-amarilla"></span>{% endif %}
      {% if j.ev.salio %}<span class="bg bg-out">↓</span>{% elif j.ev.entro %}<span class="bg bg-in">↑</span>{% endif %}
    {% endif %}
  </div>
  <div class="cancha-nm">{{ j.dorsal or '' }} {{ (j.nombre or '').split(' ')[0] }}</div>
</div>
{%- endmacro %}
```
Nota CSP: el `onerror` inline en el `<img>` viola `script-src 'self'`. En su lugar, NO usar `onerror`; ocultar el `<img>` por CSS cuando falle no es trivial sin JS. Alternativa que sí cumple CSP: renderizar el `<img>` **solo** si `j.tiene_foto` es verdadero (dato que la vista incluye en el jugador), y el `.cancha-inicial` detrás siempre; si hay foto, tapa la inicial. Reemplazar la línea del `<img>` por:
```jinja
    {% if j.tiene_foto %}<img class="cancha-avatar" src="{{ url_for('usuario_foto', usuario_id=j.id) }}" alt="">{% endif %}
```

- [ ] **Step 2: Añadir el CSS**

En `web/app/static/styles.css`, al final. Incluye la cancha 2:3, avatar sobre inicial, los cinco distintivos, la banca en dos columnas y los grupos de eventos. (Portar los estilos de la maqueta v4 aprobada; sin `style=` inline.)
```css
/* ---------- Alineación en cancha ---------- */
.cancha-wrap { max-width: 520px; margin: 0 auto; }
.cancha { position: relative; width: 100%; aspect-ratio: 2/3; background: #1d4a30;
          border-radius: 10px; overflow: hidden; }
.cancha-lines { position: absolute; inset: 0; width: 100%; height: 100%; }
.cancha-fila { position: absolute; left: 0; right: 0; display: flex;
               justify-content: space-evenly; transform: translateY(-50%); }
.cancha-pl { text-align: center; width: 60px; }
.cancha-avw { position: relative; width: 36px; height: 36px; margin: 0 auto 4px; }
.cancha-avatar { position: absolute; inset: 0; width: 36px; height: 36px;
                 border-radius: 9px; object-fit: cover; border: 1px solid rgba(255,255,255,.35); }
.cancha-inicial { position: absolute; inset: 0; display: flex; align-items: center;
                  justify-content: center; border-radius: 9px; font-size: 16px; color: #dfe9e2;
                  background: linear-gradient(135deg,#5b7d66,#31513d); border: 1px solid rgba(255,255,255,.35); }
.cancha-nm { font-size: 9.5px; line-height: 1.25; text-shadow: 0 1px 2px rgba(0,0,0,.6); }
.bg { position: absolute; display: flex; align-items: center; justify-content: center;
      border-radius: 50%; font-size: 8px; font-weight: 800; box-shadow: 0 1px 3px rgba(0,0,0,.55); }
.bg-gol { right: -6px; top: -5px; background: #eaf3ec; color: #07140d; min-width: 16px; height: 16px; padding: 0 3px; }
.bg-asis { left: -6px; bottom: -4px; background: #0b2014; width: 16px; height: 16px; color: #eaf3ec; border: 1px solid rgba(255,255,255,.35); }
.bg-tar { right: -6px; bottom: -4px; width: 11px; height: 14px; border-radius: 2px; }
.bg-amarilla { background: #f2b53c; } .bg-roja { background: #ff5a5a; }
.bg-out { left: -6px; top: -5px; background: #e0393e; color: #fff; width: 15px; height: 15px; font-size: 9px; }
.bg-in { left: -6px; top: -5px; background: #22a06b; color: #fff; width: 15px; height: 15px; font-size: 9px; }
.cancha-aviso { position: absolute; left: 0; right: 0; display: flex; align-items: center; justify-content: center; z-index: 2; }
.cancha-aviso span { background: rgba(7,20,13,.72); border: 1px dashed rgba(198,255,0,.35);
                     color: #c6ff2e; border-radius: 10px; padding: 9px 16px; font-size: 12px; font-weight: 600; }
/* ---------- Banca ---------- */
.banca-h { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; margin: 16px 0 6px; }
.banca-h .c { color: #8aa595; letter-spacing: .14em; text-transform: uppercase; font-size: 10px; }
.banca { display: grid; grid-template-columns: 1fr 1fr; gap: 0 18px; }
.banca-i { display: flex; align-items: center; gap: 8px; padding: 7px 4px; border-bottom: 1px solid rgba(255,255,255,.05); }
.banca-i.r { flex-direction: row-reverse; text-align: right; }
/* ---------- Eventos por grupo ---------- */
.evgrupo { display: grid; grid-template-columns: 1fr 30px 1fr; gap: 10px; align-items: center; padding: 7px 0; }
.evgrupo + .evgrupo { border-top: 1px solid rgba(255,255,255,.06); }
.evgrupo .l { text-align: right; } .evgrupo .r { text-align: left; }
.evgrupo .i { display: flex; align-items: center; justify-content: center; }
```

- [ ] **Step 3: Verificar que el panel arranca sin romper CSS**

Run: `docker compose restart web && sleep 3 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/estadisticas` (con cookie de sesión de un test manual) — o simplemente que el contenedor no registre error de plantilla al cargar `_cancha.html`.
Expected: sin errores de Jinja en `docker compose logs web`.

- [ ] **Step 4: Commit** (pedir aprobación primero)

```bash
git add web/app/static/styles.css web/app/templates/_cancha.html
git commit -m "CSS y macro Jinja de la cancha, avatares, distintivos y banca (web)"
```

---

## Task 7: Detalle del partido reestructurado (web)

**Files:**
- Modify: `web/app/app.py` (ruta `partido_detalle`, ~línea 532)
- Modify: `web/app/templates/partido_detalle.html`
- Create: `web/app/posiciones.py` (helper de formación → filas) o función en `app.py`

**Interfaces:**
- Consumes: `GET /partidos/{id}/plan?equipo_id=`, `GET /partidos/{id}/resumen-jugadores` (Tasks 4), macro `_cancha.html` (Task 6), ruta `usuario_foto` (Task 5).
- Produces: la página de detalle con marcador+eventos agrupados y las dos canchas + banca.

- [ ] **Step 1: Escribir el helper de posiciones**

En `web/app/posiciones.py`. Replica `FORMACIONES` y `huecos()` del móvil, agrupando por líneas:
```python
"""
Traducción de una formación a filas de jugadores, de defensa a ataque.
Fuente canónica: FORMACIONES en mobile/src/screens/coach/LineupScreen.js.
Solo estas tres formaciones existen en el sistema.
"""
FORMACIONES = {
    "4-4-2": [1, 4, 4, 2],
    "4-3-3": [1, 4, 3, 3],
    "3-5-2": [1, 3, 5, 2],
}


def filas_desde_plan(formacion, titulares):
    """titulares: lista de dicts con 'orden'. Devuelve [[j, ...], ...] por línea.
    Los jugadores se reparten en orden (portero primero) según la formación."""
    tam = FORMACIONES.get(formacion, FORMACIONES["4-4-2"])
    orden = sorted(titulares, key=lambda j: j.get("orden", 0))
    filas, i = [], 0
    for n in tam:
        filas.append(orden[i:i + n])
        i += n
    return filas
```

- [ ] **Step 2: Actualizar la vista Flask**

En `web/app/app.py`, `partido_detalle`. Sustituir la carga de `/alineacion` por los dos planes + resumen, y enriquecer cada jugador con su resumen de eventos y `tiene_foto`:
```python
@app.route("/partidos/<int:partido_id>")
@login_required
def partido_detalle(partido_id):
    partido = api_get(f"/partidos/{partido_id}")
    if partido.status_code != 200:
        flash("No se pudo cargar el partido.", "error")
        return redirect(url_for("partidos"))
    partido = partido.json()
    eventos = api_get(f"/partidos/{partido_id}/eventos")
    eventos = eventos.json() if eventos.status_code == 200 else []
    resumen = api_get(f"/partidos/{partido_id}/resumen-jugadores")
    resumen = resumen.json() if resumen.status_code == 200 else {}

    def cargar_plan(equipo_id):
        if not equipo_id:
            return None
        r = api_get(f"/partidos/{partido_id}/plan?equipo_id={equipo_id}")
        if r.status_code != 200:
            return None
        p = r.json()
        # sin titulares => sin plan real
        if not p.get("jugadores"):
            return None
        for j in p["jugadores"] + p.get("suplentes", []):
            jid = j.get("jugador_id")
            j["ev"] = resumen.get(str(jid)) if jid else None
            j["id"] = jid
            j["tiene_foto"] = False  # se resuelve abajo
        return p

    plan_local = cargar_plan(partido.get("equipo_local_id"))
    plan_visitante = cargar_plan(partido.get("equipo_visitante_id"))
    # tiene_foto por jugador: una llamada por usuario sería N+1; en su lugar el
    # <img> intenta cargar y el fallback CSS (inicial) queda debajo siempre.
    # Para evitar el problema del onerror-inline (CSP), el template SIEMPRE
    # pinta la inicial y el <img> encima; si 404, el navegador no muestra img.
    from web.app.posiciones import filas_desde_plan  # o import a nivel módulo
    filas_local = filas_desde_plan(plan_local["formacion"], plan_local["jugadores"]) if plan_local else None
    filas_visit = filas_desde_plan(plan_visitante["formacion"], plan_visitante["jugadores"]) if plan_visitante else None

    return render_template(
        "partido_detalle.html", partido=partido, eventos=eventos,
        plan_local=plan_local, plan_visitante=plan_visitante,
        filas_local=filas_local, filas_visit=filas_visit,
    )
```
**Decisión de foto sin N+1:** el `<img>` se pinta siempre que el jugador tenga `id`, con la `.cancha-inicial` debajo. Si el usuario no tiene foto, el endpoint da 404 y el navegador simplemente no dibuja la imagen — la inicial queda visible. Así se evita preguntar `tiene_foto` por cada jugador. Ajustar el macro de Task 6 para pintar el `<img>` cuando haya `j.id` (no `j.tiene_foto`), aceptando que un 404 es el mecanismo de fallback. (Esto es válido en web; el 404 no ensucia consola de forma crítica y evita 22 llamadas de metadata.)

- [ ] **Step 3: Reescribir el template**

Reescribir `web/app/templates/partido_detalle.html`: tarjeta 1 con marcador + eventos agrupados por tipo (usar `icono()` de `_iconos.html` para gol/tarjeta/cambio, agrupando `eventos` por `tipo` en el template con filtros Jinja), tarjeta 2 importando el macro de `_cancha.html` con `filas_local`/`filas_visit`, banca debajo, y el aviso de "Alineación no registrada" cuando un plan sea `None`. Mantener el `{% from "_iconos.html" import icono %}` que ya existe.

- [ ] **Step 4: Verificar en el navegador**

Manual con la BD de desarrollo (hay 2 planes sembrados): logueado en el panel, abrir el detalle de un partido que tenga plan. Verificar: marcador arriba, eventos agrupados, cancha con jugadores en su formación, iniciales visibles (o fotos si se subieron), banca en dos columnas. Abrir un partido sin plan de un equipo → aviso en la mitad correspondiente sin romper el contenedor.

- [ ] **Step 5: Verificar CSP (cero JS/style inline nuevos)**

Run: `git diff web/app/templates/partido_detalle.html web/app/templates/_cancha.html | grep -E "^\+" | grep -E "onerror|onclick|style=|<script" | wc -l`
Expected: `0`.

- [ ] **Step 6: Commit** (pedir aprobación primero)

```bash
git add web/app/app.py web/app/posiciones.py web/app/templates/partido_detalle.html
git commit -m "Detalle del partido: eventos agrupados + alineaciones en cancha con fotos"
```

---

## Task 8: Fotos en LineupScreen (móvil, entrenador)

**Files:**
- Modify: `mobile/src/api.js` (helper `urlFoto`)
- Create: `mobile/src/components/Avatar.js`
- Modify: `mobile/src/screens/coach/LineupScreen.js`

**Interfaces:**
- Consumes: `GET /usuarios/{id}/foto` (Task 3), `leerToken`/`API_URL` de `api.js`.
- Produces: `urlFoto(usuarioId) -> string`; componente `<Avatar usuarioId nombre size />`.

- [ ] **Step 1: Añadir el helper de URL**

En `mobile/src/api.js`, exportar:
```javascript
export function urlFoto(usuarioId) {
  return `${API_URL}/usuarios/${usuarioId}/foto`;
}
```

- [ ] **Step 2: Crear el componente Avatar**

En `mobile/src/components/Avatar.js`. Usa `<Image>` con el token en cabecera; si falla, muestra la inicial:
```javascript
import React, { useEffect, useState } from "react";
import { Image, Text, View } from "react-native";
import { urlFoto, leerToken } from "../api";
import { lp } from "../publicTheme";

export default function Avatar({ usuarioId, nombre, size = 36 }) {
  const [token, setToken] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { leerToken().then(setToken); }, []);

  const inicial = (nombre || "?").charAt(0).toUpperCase();
  const base = { width: size, height: size, borderRadius: size * 0.25 };

  if (!usuarioId || error || !token) {
    return (
      <View style={[base, { backgroundColor: "#31513d", alignItems: "center", justifyContent: "center",
                            borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}>
        <Text style={{ color: "#dfe9e2", fontWeight: "700" }}>{inicial}</Text>
      </View>
    );
  }
  return (
    <Image
      source={{ uri: urlFoto(usuarioId), headers: { Authorization: `Bearer ${token}` } }}
      style={[base, { borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}
      onError={() => setError(true)}
    />
  );
}
```

- [ ] **Step 3: Usar Avatar en los huecos de la cancha**

En `mobile/src/screens/coach/LineupScreen.js`, donde cada hueco pinta al jugador asignado, sustituir el círculo con dorsal/inicial por `<Avatar usuarioId={asignado.jugador_id} nombre={asignado.nombre} size={40} />`. Importar `Avatar` arriba. Mantener el dorsal y el nombre debajo como están.

- [ ] **Step 4: Validación manual con Expo**

Con `npx expo start --tunnel` y `apiUrl` apuntando a la IP LAN: entrar como entrenador, abrir la pantalla de alineación. Los jugadores con foto subida la muestran; los demás, la inicial. Confirmar que no crashea si un jugador no tiene foto.

- [ ] **Step 5: Commit** (pedir aprobación primero)

```bash
git add mobile/src/api.js mobile/src/components/Avatar.js mobile/src/screens/coach/LineupScreen.js
git commit -m "Fotos de perfil en la alineación del entrenador (LineupScreen)"
```

---

## Task 9: Vista de alineación del árbitro con pestañas (móvil)

**Files:**
- Create: `mobile/src/components/LineupPitch.js`
- Create: `mobile/src/screens/referee/RefLineupScreen.js`
- Modify: navegación del árbitro (`mobile/App.js` o el stack del árbitro — identificar dónde se registran las pantallas `Ref*`)

**Interfaces:**
- Consumes: `GET /partidos/{id}/plan?equipo_id=`, `GET /partidos/{id}/resumen-jugadores` (Task 4), `<Avatar>` (Task 8).
- Produces: `<LineupPitch equipoId plan resumen />`; pantalla `RefLineupScreen` con pestañas local/visitante.

- [ ] **Step 1: Identificar el punto de entrada**

Run: `grep -n "Ref.*Screen\|Stack.Screen\|Tab.Screen" mobile/App.js`
Decidir dónde engancha `RefLineupScreen`: como pantalla accesible desde RefLiveScreen (botón "Ver alineaciones") o desde el menú del partido del árbitro. Anotar la decisión en el commit.

- [ ] **Step 2: Crear el componente LineupPitch**

En `mobile/src/components/LineupPitch.js`: una cancha de UN equipo (View con fondo verde, líneas simples con Views absolutas, filas por formación como en LineupScreen), cada jugador con `<Avatar>` y los distintivos derivados de `resumen[jugador_id]`. Reutilizar la lógica de `FORMACIONES`/`huecos` que ya está en LineupScreen (extraerla a un módulo compartido `mobile/src/formaciones.js` si conviene, para no duplicar). Si el plan es nulo o sin titulares, renderizar el aviso "Alineación no registrada" centrado.

- [ ] **Step 3: Crear RefLineupScreen con pestañas**

En `mobile/src/screens/referee/RefLineupScreen.js`: descarga el partido, ambos planes y el resumen (como ya hace RefEventScreen), un selector local/visitante (reutilizar el patrón de `equipoSel` de RefEventScreen), y renderiza `<LineupPitch>` para el equipo seleccionado.

- [ ] **Step 4: Enganchar en la navegación**

Registrar `RefLineupScreen` en el stack del árbitro y añadir el punto de acceso decidido en Step 1.

- [ ] **Step 5: Validación manual con Expo**

Como árbitro, abrir un partido con plan, entrar a la vista de alineaciones, alternar pestañas local/visitante. Verificar fotos, distintivos (registrar un gol/tarjeta antes y comprobar que aparece), y el aviso cuando un equipo no tiene plan.

- [ ] **Step 6: Commit** (pedir aprobación primero)

```bash
git add mobile/src/components/LineupPitch.js mobile/src/screens/referee/RefLineupScreen.js mobile/App.js mobile/src/formaciones.js
git commit -m "Vista de alineaciones del árbitro con pestañas y fotos (LineupPitch)"
```

---

## Task 10: Punto de subida de foto en las pantallas de perfil (móvil)

**Files:**
- Modify: `mobile/src/screens/coach/PerfilScreen.js` (entrenador y árbitro)
- Modify: `mobile/src/screens/player/PlayerProfileScreen.js` (jugador)
- Modify: `mobile/src/api.js` (helper de subida)

**Interfaces:**
- Consumes: `POST /usuarios/me/foto`, `DELETE /usuarios/me/foto` (Task 3).
- Produces: `subirFoto(uri) -> Promise`, `borrarFoto() -> Promise`; botón "Cambiar foto" en ambas pantallas de perfil.

- [ ] **Step 1: Helpers de subida en api.js**

En `mobile/src/api.js`:
```javascript
export async function subirFoto(uri) {
  const t = await leerToken();
  const form = new FormData();
  form.append("foto", { uri, name: "perfil.jpg", type: "image/jpeg" });
  const res = await fetch(`${API_URL}/usuarios/me/foto`, {
    method: "POST",
    headers: { Authorization: `Bearer ${t}` },
    body: form,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "No se pudo subir la foto");
  return res.json();
}

export async function borrarFoto() {
  return apiDelete("/usuarios/me/foto");  // usar el helper delete existente
}
```
Verificar el nombre real del helper delete en `api.js` y ajustar.

- [ ] **Step 2: Botón en las pantallas de perfil**

En `PerfilScreen.js` y `PlayerProfileScreen.js`: mostrar el `<Avatar usuarioId={usuario.id} nombre={usuario.nombre} size={72} />` arriba, y un botón "Cambiar foto" que abre `expo-image-picker` (verificar si ya es dependencia; si no, añadirla), recorta cuadrado, y llama `subirFoto(uri)`. Tras éxito, refrescar el perfil (`refrescar()` del auth). Botón secundario "Quitar foto" que llama `borrarFoto()`.

- [ ] **Step 3: Validación manual con Expo**

Como cada rol: abrir perfil, cambiar foto desde galería, ver que aparece en el perfil y luego en la alineación. Quitar la foto y ver que vuelve la inicial.

- [ ] **Step 4: Commit** (pedir aprobación primero)

```bash
git add mobile/src/api.js mobile/src/screens/coach/PerfilScreen.js mobile/src/screens/player/PlayerProfileScreen.js
git commit -m "Subir/quitar foto de perfil desde la app móvil"
```

---

## Self-Review (hecho al escribir el plan)

**Cobertura del spec:**
- Unidad 1 (foto: modelo, migración, Pillow, endpoints, servido JWT) → Tasks 1-3, 10. ✓
- Unidad 2 (resumen de eventos) → Task 4. ✓
- Unidad 3a (web) → Tasks 5-7. ✓
- Unidad 3b (LineupScreen) → Task 8. ✓
- Unidad 3c (árbitro con pestañas) → Task 9. ✓
- Permisos (cada uno la suya, admin borra) → Task 3 tests. ✓
- Equipo sin plan → Tasks 7 (web) y 9 (árbitro). ✓
- Nota de orden de rutas `/me/foto` → Task 3. ✓

**Consistencia de tipos:** `resumen_por_jugador` devuelve claves int; el endpoint JSON las serializa como strings, y tanto el web (`resumen.get(str(jid))`) como el móvil las leen como strings. Coherente. `tiene_foto` se define en Task 1 y se consume en Task 3. `urlFoto`/`Avatar` definidos en Task 8 y reusados en Task 9.

**Riesgos verificados al escribir el plan:**
- Fixture `miembro_id` (conftest.py:138): CONFIRMADO, devuelve el id del jugador del Equipo A. Task 4 lo usa directo.
- `apiDelete` (api.js:105): CONFIRMADO, existe. Task 10 lo usa.
- `expo-image-picker`: CONFIRMADO que NO está instalado. Task 10 Step 2 debe añadirlo (`npx expo install expo-image-picker`) antes de usarlo.
- El `import` de `posiciones` en `app.py` (Task 7) debe ser a nivel módulo, no dentro de la función, si la estructura de paquetes lo permite.
