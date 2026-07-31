# Notificaciones para árbitro y entrenador — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el árbitro se entere de sus designaciones y cambios de partido, y el entrenador de torneos nuevos, partidos de su equipo y el resultado de sus inscripciones — con campana en ambos paneles.

**Architecture:** La infraestructura entera ya existe (`notificaciones_service.crear_notificacion` = BD + push best-effort; endpoints; pantalla). Esta rama solo añade **llamadas** en los endpoints que generan los eventos (partidos, torneos, inscripciones, pagos_service) y **acceso** en el móvil (campana compartida + dos registros más de la misma pantalla). Sin migración, sin columna nueva, sin pantalla nueva.

**Tech Stack:** FastAPI (`api/`), pytest, React Native / Expo SDK 51 (`mobile/`).

## Global Constraints

- `notificaciones_service.crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)` es **la única puerta**: no crear `models.Notificacion` a mano fuera de tests. **No hace commit** — el endpoint comete después de llamarla.
- **Deduplicar destinatarios en avisos de partido**: en el seed y en los tests el MISMO entrenador dirige a los dos equipos; debe recibir UN aviso por evento, no dos.
- `actualizar_partido` hace `setattr` ciego sobre `cambios`: **capturar `arbitro_id`/`fecha_hora`/`cancha_id` ANTES del loop** o no hay forma de saber qué cambió. Ojo: el loop usa la variable local `campo`, que sombrea el módulo `campo` importado — es preexistente e inofensivo mientras no se llame al módulo dentro de esa función; no lo "arregles".
- En `eliminar_partido`, capturar nombres e ids **antes** de `db.delete`.
- Los tests de avisos usan **deltas antes/después** de `GET /notificaciones` (nunca conteos absolutos): los fixtures ya generan avisos (p. ej. crear el torneo del fixture notificará al entrenador en cuanto exista ese trigger).
- Un aviso a quien ya recibe "Pago confirmado" por el mismo acto es ruido: "Inscripción aceptada" solo va al entrenador cuando **hoy nadie se lo dice** (torneo gratis, o pagó/confirmó otro usuario).
- Mensajes y comentarios en español. Títulos: son el discriminador de icono en la pantalla — usar exactamente "Partido asignado", "Cambio de designación", "Partido reprogramado", "Partido cancelado", "Torneo nuevo", "Inscripción aceptada".
- Tests desde `api/` con `.venv/bin/pytest`, solo archivos afectados por tarea; suite completa al final de la rama (~13-19 min, **timeout de 25 min, en primer plano**). Móvil: `cd mobile && npm run verificar` (⚠️ nunca `npx babel`).
- ⚠️ `mobile/app.json` tiene un cambio local ajeno. Nunca `git add -A` ni `git commit -a`.
- Esta rama sale de `feat/inscribir-equipos` (feature B): toca las mismas zonas de `App.js`/`CoachHomeScreen.js` y los números de línea de abajo lo asumen.

---

### Task 1: Avisos al crear un partido

**Files:**
- Modify: `api/app/routers/partidos.py` (imports; helper nuevo; `crear_partido`)
- Test: `api/tests/test_avisos.py` (nuevo)

**Interfaces:**
- Consumes: `notificaciones_service.crear_notificacion` (firma arriba).
- Produces: helper `_avisar_partido(db, background_tasks, titulo, mensaje, usuario_ids)` que reutilizan las Tasks 2 y 3, y el archivo `test_avisos.py` con el helper `_notis` que reutilizan todas.

- [ ] **Step 1: Tests que fallan**

Crear `api/tests/test_avisos.py`:

```python
"""Avisos de negocio para árbitro y entrenador (partidos, torneos, inscripciones).

Todos los conteos son DELTAS antes/después: los fixtures ya generan avisos
propios (p. ej. el torneo del fixture avisará a los entrenadores).
"""


def _notis(client, auth):
    return client.get("/notificaciones", headers=auth).json()


def _crear_partido(client, auth_admin, torneo_id, arbitro_id=None, **over):
    body = {"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}
    if arbitro_id:
        body["arbitro_id"] = arbitro_id
    body.update(over)
    return client.post("/partidos", headers=auth_admin, json=body)


def test_crear_partido_avisa_al_arbitro(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    antes = len(_notis(client, auth_arbitro))
    r = _crear_partido(client, auth_admin, torneo_id, arbitro_id)
    assert r.status_code == 201
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Partido asignado"


def test_crear_partido_sin_arbitro_no_lo_avisa(client, auth_admin, auth_arbitro, torneo_id):
    antes = len(_notis(client, auth_arbitro))
    assert _crear_partido(client, auth_admin, torneo_id).status_code == 201
    assert len(_notis(client, auth_arbitro)) == antes


def test_crear_partido_avisa_una_vez_al_entrenador_de_ambos_equipos(
        client, auth_admin, auth_entrenador, arbitro_id, torneo_id):
    """Los equipos 1 y 2 son del MISMO entrenador: un aviso, no dos."""
    antes = len(_notis(client, auth_entrenador))
    _crear_partido(client, auth_admin, torneo_id, arbitro_id)
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Partido programado"
```

- [ ] **Step 2: Verlos fallar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py -v`
Expected: los 3 FALLAN (delta 0 donde se espera 1, o título ausente). El de "sin árbitro" también corre (pasará trivialmente hasta que exista el trigger; se queda como guard).

- [ ] **Step 3: Implementar**

En `api/app/routers/partidos.py`:

1. Línea 16, añadir `BackgroundTasks` al import de fastapi:

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
```

2. Línea 20, añadir el servicio:

```python
from app import campo, eventos_resumen, models, notificaciones_service
```

3. Encima de `crear_partido` (hoy línea ~76), el helper:

```python
def _avisar_partido(db, background_tasks, titulo: str, mensaje: str, usuario_ids) -> None:
    """Un aviso por usuario, sin repetir: el mismo entrenador puede dirigir a
    los dos equipos del partido. Los None se ignoran (partido sin árbitro)."""
    for uid in dict.fromkeys(u for u in usuario_ids if u):
        notificaciones_service.crear_notificacion(db, uid, titulo, mensaje, background_tasks)
```

4. En `crear_partido`: añadir el parámetro `background_tasks: BackgroundTasks,` después de `datos: PartidoCreate,`, y tras el `db.refresh(partido)` final, antes del `return`:

```python
    # Avisos: al árbitro designado y a los entrenadores de ambos equipos.
    rivales = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
    cuando = f" el {partido.fecha_hora:%d/%m %H:%M}" if partido.fecha_hora else ""
    if partido.arbitro_id:
        _avisar_partido(db, background_tasks, "Partido asignado",
                        f"Pitarás {rivales}{cuando}.", [partido.arbitro_id])
    _avisar_partido(db, background_tasks, "Partido programado",
                    f"Tu equipo juega {rivales}{cuando}.",
                    [partido.equipo_local.entrenador_id, partido.equipo_visitante.entrenador_id])
    db.commit()
```

- [ ] **Step 4: Verlos pasar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py tests/test_partidos.py -v`
Expected: todo PASSED (los de `test_partidos.py` confirman que añadir el parámetro no rompió nada).

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_avisos.py
git commit -m "feat(api): avisar al arbitro y entrenadores al crear un partido"
```

---

### Task 2: Avisos al reprogramar o reasignar un partido

**Files:**
- Modify: `api/app/routers/partidos.py` (`actualizar_partido`)
- Test: `api/tests/test_avisos.py`

**Interfaces:**
- Consumes: `_avisar_partido` (Task 1), `_crear_partido`/`_notis` de `test_avisos.py`.
- Produces: nada nuevo.

- [ ] **Step 1: Tests que fallan**

Al final de `api/tests/test_avisos.py`:

```python
def test_cambiar_fecha_avisa_a_arbitro_y_entrenador(client, auth_admin, auth_arbitro,
                                                    auth_entrenador, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes_arb = len(_notis(client, auth_arbitro))
    antes_ent = len(_notis(client, auth_entrenador))
    r = client.put(f"/partidos/{pid}", headers=auth_admin, json={"fecha_hora": "2027-01-15T18:00:00"})
    assert r.status_code == 200
    notis_arb = _notis(client, auth_arbitro)
    assert len(notis_arb) == antes_arb + 1 and notis_arb[0]["titulo"] == "Partido reprogramado"
    assert len(_notis(client, auth_entrenador)) == antes_ent + 1


def test_asignar_arbitro_despues_lo_avisa(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id).json()["id"]  # sin árbitro
    antes = len(_notis(client, auth_arbitro))
    client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": arbitro_id})
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1 and notis[0]["titulo"] == "Partido asignado"


def test_quitar_al_arbitro_lo_avisa(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes = len(_notis(client, auth_arbitro))
    r = client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": None})
    assert r.status_code == 200
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1 and notis[0]["titulo"] == "Cambio de designación"


def test_actualizar_sin_cambios_relevantes_no_avisa(client, auth_admin, auth_arbitro,
                                                    arbitro_id, torneo_id):
    """Repetir el mismo árbitro no es un cambio: nadie recibe nada."""
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes = len(_notis(client, auth_arbitro))
    client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": arbitro_id})
    assert len(_notis(client, auth_arbitro)) == antes
```

- [ ] **Step 2: Verlos fallar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py -v`
Expected: los 3 primeros nuevos FALLAN; el de "sin cambios relevantes" pasa trivialmente (guard).

- [ ] **Step 3: Implementar**

En `actualizar_partido`: añadir `background_tasks: BackgroundTasks,` después de `datos: PartidoUpdate,`. Justo después de `cambios = datos.model_dump(exclude_unset=True)`:

```python
    # El loop de abajo es un setattr ciego: sin esta foto previa no hay forma
    # de saber qué cambió de verdad para avisar solo a quien corresponde.
    previo = {"arbitro_id": partido.arbitro_id, "fecha_hora": partido.fecha_hora,
              "cancha_id": partido.cancha_id}
```

Y tras el `db.refresh(partido)` final, antes del `return`:

```python
    rivales = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
    cuando = f" el {partido.fecha_hora:%d/%m %H:%M}" if partido.fecha_hora else ""
    if "arbitro_id" in cambios and cambios["arbitro_id"] != previo["arbitro_id"]:
        _avisar_partido(db, background_tasks, "Partido asignado",
                        f"Pitarás {rivales}{cuando}.", [partido.arbitro_id])
        _avisar_partido(db, background_tasks, "Cambio de designación",
                        f"Ya no pitarás {rivales}.", [previo["arbitro_id"]])
    if (("fecha_hora" in cambios and cambios["fecha_hora"] != previo["fecha_hora"])
            or ("cancha_id" in cambios and cambios["cancha_id"] != previo["cancha_id"])):
        _avisar_partido(db, background_tasks, "Partido reprogramado",
                        f"{rivales}: nueva programación{cuando}.",
                        [partido.arbitro_id, partido.equipo_local.entrenador_id,
                         partido.equipo_visitante.entrenador_id])
    db.commit()
```

(`_avisar_partido` ignora `None`, así que asignar o quitar árbitro no necesita casos aparte. ⚠️ `cambios["fecha_hora"]` ya pasó por Pydantic: es `datetime`, comparable con `previo["fecha_hora"]` directamente.)

- [ ] **Step 4: Verlos pasar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py tests/test_partidos.py -v`
Expected: todo PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_avisos.py
git commit -m "feat(api): avisar reprogramaciones y cambios de designacion"
```

---

### Task 3: Aviso al eliminar un partido

**Files:**
- Modify: `api/app/routers/partidos.py` (`eliminar_partido`)
- Test: `api/tests/test_avisos.py`

**Interfaces:**
- Consumes: `_avisar_partido` (Task 1).
- Produces: nada nuevo.

- [ ] **Step 1: Test que falla**

Al final de `api/tests/test_avisos.py`:

```python
def test_eliminar_partido_avisa(client, auth_admin, auth_arbitro, auth_entrenador,
                                arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes_arb = len(_notis(client, auth_arbitro))
    antes_ent = len(_notis(client, auth_entrenador))
    assert client.delete(f"/partidos/{pid}", headers=auth_admin).status_code == 204
    notis_arb = _notis(client, auth_arbitro)
    assert len(notis_arb) == antes_arb + 1 and notis_arb[0]["titulo"] == "Partido cancelado"
    assert len(_notis(client, auth_entrenador)) == antes_ent + 1
```

- [ ] **Step 2: Verlo fallar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py -k eliminar -v`
Expected: FALLA (deltas en 0).

- [ ] **Step 3: Implementar**

En `eliminar_partido`: añadir `background_tasks: BackgroundTasks,` después de `partido_id: int,`, y reemplazar el cuerpo final:

```python
    partido = _obtener_partido(db, partido_id)
    db.delete(partido)
    db.commit()
```

por:

```python
    partido = _obtener_partido(db, partido_id)
    # La foto va ANTES del delete: después ya no hay relaciones que leer.
    rivales = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
    avisar = [partido.arbitro_id, partido.equipo_local.entrenador_id,
              partido.equipo_visitante.entrenador_id]
    db.delete(partido)
    _avisar_partido(db, background_tasks, "Partido cancelado",
                    f"Se canceló {rivales}.", avisar)
    db.commit()
```

- [ ] **Step 4: Verlo pasar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py tests/test_partidos.py -q`
Expected: todo PASSED (en particular `test_borrar_partido_con_alineacion_y_eventos`, que confirma que el aviso convive con la cascada del PR #25).

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_avisos.py
git commit -m "feat(api): avisar cuando se cancela un partido"
```

---

### Task 4: "Torneo nuevo" a todos los entrenadores

**Files:**
- Modify: `api/app/routers/torneos.py` (import + `crear_torneo`)
- Test: `api/tests/test_avisos.py`

**Interfaces:**
- Consumes: `notificaciones_service.crear_notificacion`.
- Produces: nada nuevo.

- [ ] **Step 1: Tests que fallan**

Al final de `api/tests/test_avisos.py`:

```python
def test_torneo_nuevo_avisa_a_los_entrenadores(client, auth_admin, auth_entrenador):
    antes = len(_notis(client, auth_entrenador))
    r = client.post("/torneos", headers=auth_admin, json={"nombre": "Copa Avisos", "sede_id": 1})
    assert r.status_code == 201
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Torneo nuevo"
    assert "Copa Avisos" in notis[0]["mensaje"]


def test_torneo_nuevo_no_avisa_a_jugadores(client, auth_admin):
    tok = client.post("/auth/login", json={"correo": "miembro@demo.com", "password": "miembropass123"}).json()["access_token"]
    auth_miembro = {"Authorization": f"Bearer {tok}"}
    antes = len(_notis(client, auth_miembro))
    client.post("/torneos", headers=auth_admin, json={"nombre": "Copa Silencio", "sede_id": 1})
    assert len(_notis(client, auth_miembro)) == antes
```

- [ ] **Step 2: Verlos fallar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py -k torneo_nuevo -v`
Expected: el primero FALLA; el segundo pasa trivialmente (guard).

- [ ] **Step 3: Implementar**

En `api/app/routers/torneos.py`:

1. Añadir `BackgroundTasks` al import de fastapi y `notificaciones_service` al import de `app` (mismo patrón que la Task 1).
2. En `crear_torneo`: añadir `background_tasks: BackgroundTasks,` después de `datos: TorneoCreate,`, y tras el `db.refresh(torneo)`, antes del `return`:

```python
    # Aviso a TODOS los entrenadores: un torneo no pertenece a nadie hasta que
    # hay inscripciones, así que no existe otra audiencia posible.
    cierre = (f" Inscripciones hasta el {torneo.fecha_cierre_inscripciones:%d/%m/%Y}."
              if torneo.fecha_cierre_inscripciones else "")
    entrenadores = (
        db.query(models.Usuario.id)
        .join(models.Rol, models.Usuario.rol_id == models.Rol.id)
        .filter(models.Rol.nombre == "entrenador")
        .all()
    )
    for (uid,) in entrenadores:
        notificaciones_service.crear_notificacion(
            db, uid, "Torneo nuevo", f"Ya abrió {torneo.nombre}.{cierre}", background_tasks)
    db.commit()
```

- [ ] **Step 4: Verlos pasar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py tests/test_torneos.py -v`
Expected: todo PASSED. (Si `tests/test_torneos.py` no existe con ese nombre, localizar el archivo de tests de torneos con `ls api/tests/ | grep torneo` y correr ese.)

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/torneos.py api/tests/test_avisos.py
git commit -m "feat(api): avisar a los entrenadores cuando abre un torneo"
```

---

### Task 5: "Inscripción aceptada" cuando hoy nadie lo dice

**Files:**
- Modify: `api/app/routers/inscripciones.py` (import + `crear_inscripcion`)
- Modify: `api/app/pagos_service.py` (`pagar_inscripcion`, `confirmar_pago`)
- Test: `api/tests/test_avisos.py`

**Interfaces:**
- Consumes: `notificaciones_service.crear_notificacion`; `_notificar` ya existente en `pagos_service.py`.
- Produces: nada nuevo.

Regla: el aviso va al `equipo.entrenador_id` SOLO cuando hoy nadie se lo dice — torneo gratis (aceptación directa silenciosa) o cuando el pagador/confirmador es **otro** usuario. Si el propio entrenador paga, su "Pago confirmado" ya es el aviso: no duplicar.

- [ ] **Step 1: Tests que fallan**

Al final de `api/tests/test_avisos.py`:

```python
def _torneo(client, auth_admin, **over):
    body = {"nombre": "Copa Inscripción", "sede_id": 1}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def test_inscripcion_gratis_avisa_aceptada(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)  # sin cuota -> aceptada directa
    antes = len(_notis(client, auth_entrenador))
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 201 and r.json()["estado"] == "aceptada"
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Inscripción aceptada"


def test_pago_de_otro_avisa_al_entrenador(client, auth_admin, auth_entrenador):
    """El admin paga la cuota en nombre del equipo: el entrenador (que no fue
    el pagador) recibe el aviso de aceptación."""
    tid = _torneo(client, auth_admin, cuota_inscripcion=500)
    iid = client.post("/inscripciones", headers=auth_entrenador,
                      json={"torneo_id": tid, "equipo_id": 1}).json()["id"]
    antes = len(_notis(client, auth_entrenador))
    r = client.post(f"/pagos/inscripcion/{iid}", headers=auth_admin, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
                    "cvv": "123", "titular": "Admin Demo"}})
    assert r.status_code == 201, r.text
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Inscripción aceptada"


def test_pago_propio_no_duplica_el_aviso(client, auth_admin, auth_entrenador):
    """El entrenador paga su propia cuota: recibe 'Pago confirmado' (existente)
    y NADA más — un solo aviso nuevo, no dos."""
    tid = _torneo(client, auth_admin, cuota_inscripcion=500)
    iid = client.post("/inscripciones", headers=auth_entrenador,
                      json={"torneo_id": tid, "equipo_id": 1}).json()["id"]
    antes = len(_notis(client, auth_entrenador))
    client.post(f"/pagos/inscripcion/{iid}", headers=auth_entrenador, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
                    "cvv": "123", "titular": "Entrenador Demo"}})
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Pago confirmado"
```

- [ ] **Step 2: Verlos fallar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py -k inscripcion -v`
Expected: los 2 primeros FALLAN; el tercero pasa (guard contra el duplicado).

- [ ] **Step 3: Implementar**

1. `api/app/routers/inscripciones.py`: añadir `BackgroundTasks` al import de fastapi y `notificaciones_service` al de `app`; añadir `background_tasks: BackgroundTasks,` a la firma de `crear_inscripcion`; y tras el `db.refresh(inscripcion)`, antes del `return`:

```python
    if inscripcion.estado == "aceptada":
        # Torneo sin cuota: se acepta al momento y hoy nadie avisa. Con cuota,
        # el aviso sale al completarse el pago (pagos_service).
        notificaciones_service.crear_notificacion(
            db, equipo.entrenador_id, "Inscripción aceptada",
            f"{equipo.nombre} quedó inscrito en {torneo.nombre}.", background_tasks)
        db.commit()
```

2. `api/app/pagos_service.py`, en `pagar_inscripcion`, dentro de la rama `resultado.estado == "completado"`, después del `_notificar(...)` de "Pago confirmado":

```python
        if inscripcion.equipo.entrenador_id != usuario.id:
            # Pagó otro (p. ej. el admin): el dueño del equipo no vio el pago.
            _notificar(db, inscripcion.equipo.entrenador_id, "Inscripción aceptada",
                       f"Tu {concepto} quedó pagada y aceptada.", background_tasks)
```

3. `api/app/pagos_service.py`, en `confirmar_pago`, después de `pago.inscripcion.estado = "aceptada"` (dentro de su `if`):

```python
    if pago.inscripcion is not None and pago.inscripcion.equipo.entrenador_id != pago.usuario_id:
        _notificar(db, pago.inscripcion.equipo.entrenador_id, "Inscripción aceptada",
                   f"Tu {pago.concepto} fue confirmada.", background_tasks)
```

(Colocarlo antes del `_notificar` de "Pago confirmado" que ya existe al final, y respetar que el commit lo hace la propia función.)

- [ ] **Step 4: Verlos pasar**

Run: `cd api && .venv/bin/pytest tests/test_avisos.py tests/test_inscripciones.py tests/test_pagos_inscripcion.py tests/test_pagos_transferencia.py -v`
Expected: todo PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/inscripciones.py api/app/pagos_service.py api/tests/test_avisos.py
git commit -m "feat(api): avisar al entrenador cuando su inscripcion queda aceptada"
```

---

### Task 6: Campana en los paneles de coach y árbitro

**Files:**
- Create: `mobile/src/components/Campanita.js`
- Modify: `mobile/src/screens/player/PlayerHomeScreen.js` (usa el componente compartido)
- Modify: `mobile/src/screens/coach/CoachHomeScreen.js` (campana dorada)
- Modify: `mobile/src/screens/referee/RefMatchesScreen.js` (campana blanca)
- Modify: `mobile/src/screens/player/NotificationsScreen.js` (icono para "partido")
- Modify: `mobile/App.js` (dos registros más de la pantalla)

**Interfaces:**
- Consumes: `GET /notificaciones` (`[{leida, titulo, ...}]`), pantalla `NotificationsScreen` (ya importada en `App.js`), `goldHeader`/`maroonHeader` de `App.js`.
- Produces: componente `Campanita {onPress, hayNuevas, color}`; rutas `NotificationsCoach` y `NotificationsRef`.

- [ ] **Step 1: Extraer la campana**

Crear `mobile/src/components/Campanita.js`:

```jsx
// Campana de cabecera con punto rojo de "hay avisos sin leer".
// El color depende de la cabecera de cada panel (verde/dorada/guinda).
import React from "react";
import { TouchableOpacity, View } from "react-native";
import Icono from "./Icono";
import { lp } from "../publicTheme";

export default function Campanita({ onPress, hayNuevas, color = lp.white }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ paddingHorizontal: 14 }}>
      <Icono nombre="bell" size={20} color={color} />
      {/* El glifo de la campana no llena el viewBox de 24 (deja aire a los
          lados y arriba), así que el punto va más adentro y más arriba para
          apoyarse en la esquina superior derecha real. */}
      {hayNuevas && <View style={{ position: "absolute", right: 11, top: -4, width: 10, height: 10, borderRadius: 5, backgroundColor: lp.red }} />}
    </TouchableOpacity>
  );
}
```

- [ ] **Step 2: `PlayerHomeScreen` usa el compartido**

En `mobile/src/screens/player/PlayerHomeScreen.js`: borrar la función local `Campanita` (líneas 12-23) y su comentario, y añadir el import:

```js
import Campanita from "../../components/Campanita";
```

Nada más cambia: el `useLayoutEffect` existente ya le pasa `hayNuevas`/`onPress`, y el color por defecto (blanco) es el que ya tenía.

- [ ] **Step 3: Campana dorada en el inicio del coach**

En `mobile/src/screens/coach/CoachHomeScreen.js`:

1. Imports: añadir `useLayoutEffect` al import de React y el componente:

```js
import React, { useCallback, useLayoutEffect, useState } from "react";
import Campanita from "../../components/Campanita";
```

2. Dentro del componente, junto a los `useState` existentes:

```js
  const [hayNuevas, setHayNuevas] = useState(false);

  useLayoutEffect(() => {
    navigation.setOptions({
      // La cabecera del coach es dorada: la campana va en el tono del texto dorado.
      headerRight: () => <Campanita hayNuevas={hayNuevas} color={lp.goldText}
        onPress={() => navigation.navigate("NotificationsCoach")} />,
    });
  }, [navigation, hayNuevas]);
```

3. Reemplazar el cuerpo del `try` del `useFocusEffect` (hoy `setResumen(await apiGet("/equipos/resumen"));`) por:

```js
          const [res, notis] = await Promise.all([
            apiGet("/equipos/resumen"),
            apiGet("/notificaciones"),
          ]);
          setResumen(res);
          setHayNuevas(notis.some((n) => !n.leida));
```

(El `catch` existente que hace `setResumen(null)` se queda igual.)

- [ ] **Step 4: Campana blanca en el inicio del árbitro**

En `mobile/src/screens/referee/RefMatchesScreen.js`:

1. Imports:

```js
import React, { useCallback, useLayoutEffect, useState } from "react";
import Campanita from "../../components/Campanita";
```

2. Junto a los `useState`:

```js
  const [hayNuevas, setHayNuevas] = useState(false);

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => <Campanita hayNuevas={hayNuevas}
        onPress={() => navigation.navigate("NotificationsRef")} />,
    });
  }, [navigation, hayNuevas]);
```

3. En `cargar`, ampliar el `Promise.all`:

```js
      const [prog, vivo, notis] = await Promise.all([
        apiGet("/partidos?mios=true&estado=programado"),
        apiGet("/partidos?mios=true&estado=en_juego"),
        apiGet("/notificaciones"),
      ]);
      setPartidos([...vivo, ...prog]);
      setHayNuevas(notis.some((n) => !n.leida));
```

(El `catch` existente se queda igual.)

- [ ] **Step 5: Registrar las dos variantes de la pantalla**

En `mobile/App.js`:

1. En el bloque del entrenador, junto a `Inscribir` (feature B):

```jsx
          <Stack.Screen name="NotificationsCoach" component={NotificationsScreen} options={{ ...goldHeader, title: "NOTIFICACIONES" }} />
```

2. En el bloque del árbitro, junto a `RefSummary`:

```jsx
          <Stack.Screen name="NotificationsRef" component={NotificationsScreen} options={{ ...maroonHeader, title: "NOTIFICACIONES" }} />
```

(`NotificationsScreen` ya está importada; el registro `Notifications` verde del jugador no se toca — también es el destino del tap en un push, que no conoce el rol: limitación anotada en el spec.)

- [ ] **Step 6: Icono para los títulos de partido**

En `mobile/src/screens/player/NotificationsScreen.js`, en el mapa `ICONO`, después de la línea de `"convocatoria"`:

```js
  if (t.includes("partido") || t.includes("designación")) return { icono: "football", bg: lp.maroon };
```

- [ ] **Step 7: Verificar**

Run: `cd mobile && npm run verificar`
Expected: sin errores.

Run: `cd mobile && npm run verificar-nombres`
Expected: sin errores (la campana usa `nombre="bell"`, que ya está en el catálogo).

Run: `cd mobile && grep -rn "function Campanita" src/`
Expected: solo `src/components/Campanita.js` — la copia local del jugador ya no existe.

- [ ] **Step 8: Commit**

```bash
git add mobile/src/components/Campanita.js mobile/src/screens/player/PlayerHomeScreen.js mobile/src/screens/coach/CoachHomeScreen.js mobile/src/screens/referee/RefMatchesScreen.js mobile/src/screens/player/NotificationsScreen.js mobile/App.js
git commit -m "feat(movil): campana de notificaciones en los paneles de coach y arbitro"
```

---

## Verificación final

- [ ] Suite completa: `cd api && .venv/bin/pytest -q` → 0 failed (**timeout 25 min, primer plano**). Los fixtures crean torneos y partidos por todos lados: si algún test viejo contaba notificaciones en absoluto, aquí revienta y hay que arreglarlo respetando los deltas.
- [ ] `cd mobile && npm run verificar` y `npm run verificar-nombres` sin errores.
- [ ] En dispositivo (usuario, por la mañana): crear un partido con árbitro desde Swagger → campana con punto en el panel del árbitro; abrir la lista → el punto se apaga; crear un torneo → aviso al coach.

## Qué queda fuera, a propósito

- Flujo de rechazo de inscripciones (no existe el mecanismo; sería otra feature).
- Notificaciones en el panel web.
- Deep-link del push al evento y variante temática del tap del push (abre la lista verde sea cual sea el rol).
- Preferencias por usuario, columna `tipo`, agrupación de avisos.
