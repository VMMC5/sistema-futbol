# Reglas del partido en vivo — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el sistema sepa quién está realmente en el campo: la segunda amarilla expulsa, un jugador que no está en el campo no puede recibir eventos, y todo evento lleva minuto.

**Architecture:** Toda la regla vive en el servidor, en un módulo de solo lectura (`api/app/campo.py`) que deriva "quién está en el campo" del plan del entrenador más los eventos ya guardados (`resumen_por_jugador`). `registrar_evento` la usa para rechazar con 409 y para crear la roja automática; `_plan_a_salida` la expone al cliente como dos banderas por jugador (`en_campo`, `expulsado`). La app móvil **lee** esas banderas, no recalcula nada. Sin tabla, columna ni migración nuevas.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic v2 (`api/`), pytest (`api/tests/`), React Native / Expo SDK 51 (`mobile/`).

## Global Constraints

- **No se toca la base de datos.** Ni migración, ni `NOT NULL` en `eventos_partido.minuto`, ni corrección de datos históricos (la fila `id = 12` sin minuto se conserva). Decisión explícita del usuario.
- **El fallback de "equipo sin alineación" es obligatorio, no opcional.** Si el equipo no tiene plan, la plantilla entera cuenta como "en el campo" (menos expulsados y salidos). Sostiene los tests de eventos que ya existen: `_partido_en_juego` (`api/tests/test_arbitro_eventos.py:5-9`) crea el partido **sin plan**. Quitarlo tumba la suite. **No lo "simplifiques".**
- **Un evento puede no llevar jugador y eso es legal**: el autogol atribuido solo al equipo (`test_arbitro_eventos.py:43`) va sin `jugador_id`. Cuando el campo viene vacío la validación **se salta**, no rechaza. Igual con el asistente de un gol. Solo el `cambio` exige los dos jugadores.
- **Todos los rechazos de regla son 409**, coherentes con el resto de `partidos.py`. El 400 de "el equipo no participa" y los 422 de Pydantic no cambian.
- **El cliente no recalcula la regla**: solo lee `en_campo` / `expulsado`. Si mañana la regla cambia, cambia en un sitio.
- **Los mensajes de error van en español**, como todo el router, y dicen *por qué* el jugador no es elegible.
- Baseline verificado el 2026-07-30: **233 tests**. La suite completa tarda **~12,5 min**; durante las tareas se corren solo los archivos afectados y la suite entera al final.
- Comando de tests: desde `api/`, `.venv/bin/pytest`. Comando de la app: desde `mobile/`, `npm run verificar`. ⚠️ **`npx babel` NO sirve como verificador en este repo.**

## Dos precisiones sobre el spec, encontradas leyendo el código

Ambas salen del choque entre el fallback sin alineación y las reglas del cambio. Están resueltas dentro del plan; se documentan aquí para que quien ejecute no crea que son improvisaciones:

1. **La comprobación "el que entra NO debe estar en el campo" solo se aplica cuando hay plan.** Sin plan, la plantilla entera está "en el campo", así que esa condición sería imposible de cumplir y **rompería `test_cambio_con_jugador_que_entra` (`test_arbitro_eventos.py:65-74`)**, que registra un cambio en un partido sin alineación. Con plan, el suplente no está en el campo y la comprobación funciona tal como pide el spec. Lo que sí se comprueba siempre es que el que entra no esté expulsado.
2. **`PlanItemOut` gana dos banderas, no una: `en_campo` y `expulsado`.** El spec pide que la lista de "quién entra" del cliente sean "los que **no** están en el campo y **no** están expulsados". Con solo `en_campo`, un expulsado aparecería en esa lista (no está en el campo, precisamente por estar expulsado). `expulsado` es el mínimo dato extra para cumplir la regla del spec sin que el cliente recalcule nada.

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `api/app/campo.py` **(nuevo)** | Única definición de la regla "quién está en el campo". Solo lee. | 2 |
| `api/app/schemas.py` | `EventoCreate.minuto` requerido; `PlanItemOut` gana `en_campo` y `expulsado`. | 1, 5 |
| `api/app/routers/partidos.py` | `registrar_evento` valida y crea la roja automática; `_plan_a_salida` rellena las banderas. | 3, 4, 5 |
| `api/tests/test_campo.py` **(nuevo)** | Tests unitarios de la regla, contra la sesión de BD. | 2 |
| `api/tests/test_arbitro_eventos.py` | Tests de las reglas nuevas vía API (minuto, 409, doble amarilla, banderas del plan). | 1, 3, 4, 5 |
| `api/tests/test_partidos.py`, `api/tests/test_estadisticas.py` | 4 tests existentes que hoy registran eventos sin minuto. | 1 |
| `mobile/src/screens/referee/RefEventScreen.js` | Filtra las listas por las banderas del servidor y exige el minuto. | 6 |

`campo.py` es módulo aparte y no una función dentro del router porque lo consumen **dos** sitios (`registrar_evento` y `_plan_a_salida`) y porque así se puede probar sin pasar por HTTP, igual que se hizo con `eventos_resumen.py`.

## Orden de las tareas

1. `minuto` obligatorio en el API (rompe 4 tests existentes: se arreglan aquí).
2. `campo.py`: la regla.
3. `registrar_evento` valida (409).
4. La segunda amarilla expulsa.
5. `en_campo` / `expulsado` en la salida del plan.
6. La app móvil filtra y exige el minuto.

Las tareas 1–5 son backend y cada una deja la suite en verde. La 6 no toca Python.

---

### Task 1: `minuto` obligatorio en el API

**Files:**
- Modify: `api/app/schemas.py:196`
- Modify: `api/tests/test_partidos.py:82`, `:89`, `:96`
- Modify: `api/tests/test_estadisticas.py:93`
- Test: `api/tests/test_arbitro_eventos.py` (dos tests nuevos al final)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `EventoCreate.minuto: int` (requerido, `ge=0, le=130`). Todas las tareas siguientes asumen que un POST a `/partidos/{id}/eventos` sin `minuto` responde **422** antes de entrar al router.

⚠️ **Ojo con `test_partidos.py:89`.** Envía `"equipo_id": 99` y afirma un **400** ("El equipo no participa en este partido"). Pydantic corre **antes** que el router: sin minuto ese test pasaría a 422 y dejaría de probar lo que pretende. Necesita el minuto para llegar al 400. **No relajes la aserción a `in (400, 422)`.**

⚠️ Los cuatro tests que se tocan **no están probando el minuto**: lo omitían porque se podía. Añádeles un minuto cualquiera. **No los conviertas en tests de que el minuto es opcional**: contradiría la regla nueva.

- [ ] **Step 1: Escribir los tests que fallan**

Al final de `api/tests/test_arbitro_eventos.py`:

```python
def test_evento_sin_minuto_es_422(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1})
    assert r.status_code == 422


def test_evento_con_minuto_fuera_de_rango_es_422(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    for minuto in (-1, 131):
        r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
            "tipo": "gol", "equipo_id": 1, "minuto": minuto})
        assert r.status_code == 422
```

- [ ] **Step 2: Correrlos para ver que el primero falla**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py -k "minuto" -v`
Expected: `test_evento_sin_minuto_es_422` FALLA (devuelve 201, no 422). El de fuera de rango ya pasa: ese rango existe hoy.

- [ ] **Step 3: Hacer el campo requerido**

En `api/app/schemas.py:196`, dentro de `class EventoCreate`, cambiar:

```python
    minuto: int | None = Field(default=None, ge=0, le=130)
```

por:

```python
    minuto: int = Field(ge=0, le=130)   # obligatorio: un evento sin minuto no dice cuándo pasó
```

- [ ] **Step 4: Correr los tests nuevos**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py -k "minuto" -v`
Expected: 2 PASSED.

- [ ] **Step 5: Arreglar los cuatro tests que ahora fallan**

Run primero para verlos caer: `cd api && .venv/bin/pytest tests/test_partidos.py tests/test_estadisticas.py -q`
Expected: 4 FAILED (422 donde esperaban 409 / 400 / 201).

`api/tests/test_partidos.py:82` — de:

```python
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1})
```

a:

```python
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 10})
```

`api/tests/test_partidos.py:89` — de:

```python
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 99})
```

a:

```python
    # El minuto va porque Pydantic corre antes que el router: sin él este test
    # devolvería 422 y dejaría de probar el 400 del equipo que no participa.
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 99, "minuto": 10})
```

`api/tests/test_partidos.py:96` — de:

```python
    eid = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1}).json()["id"]
```

a:

```python
    eid = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 10}).json()["id"]
```

`api/tests/test_estadisticas.py:93` — de:

```python
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1})
```

a:

```python
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 10})
```

- [ ] **Step 6: Verificar que los cuatro vuelven a verde**

Run: `cd api && .venv/bin/pytest tests/test_partidos.py tests/test_estadisticas.py tests/test_arbitro_eventos.py tests/test_eventos_resumen.py tests/test_jugador.py -q`
Expected: todo PASSED, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add api/app/schemas.py api/tests/test_partidos.py api/tests/test_estadisticas.py api/tests/test_arbitro_eventos.py
git commit -m "feat(api): el minuto es obligatorio al registrar un evento"
```

---

### Task 2: `campo.py` — la regla de quién está en el campo

**Files:**
- Create: `api/app/campo.py`
- Test: `api/tests/test_campo.py` (nuevo)

**Interfaces:**
- Consumes: `app.eventos_resumen.resumen_por_jugador(db, partido_id) -> dict[int, dict]`, que ya devuelve por jugador `{goles, asistencias, amarillas, rojas, salio, entro}`.
- Produces: `app.campo.estado_campo(db: Session, partido_id: int, equipo_id: int) -> dict` con exactamente estas cinco claves, que consumen las tareas 3, 4 y 5:
  - `en_campo: set[int]` — ids de **usuario** que pueden recibir eventos
  - `expulsados: set[int]` — con al menos una roja
  - `salidos: set[int]` — que salieron en un cambio
  - `amarillas: dict[int, int]` — amarillas por jugador
  - `hay_plan: bool` — `False` si el entrenador no registró alineación

⚠️ **Los ids son `usuarios.id`**, no `jugador_equipo_id`: los eventos, la plantilla y el plan usan todos `jugador_id = usuarios.id`. El plan guarda ambos (`jugador_equipo_id` y `jugador_id`, ver `guardar_plan` en `partidos.py:551-558`); aquí se usa siempre `jugador_id`.

⚠️ **Al escribir los tests: el plan solo se puede guardar con el partido en `programado`** (`partidos.py:525-526`). Primero `PUT /plan`, después `POST /iniciar`. Al revés da 409 y el test probaría el caso sin plan sin darse cuenta.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `api/tests/test_campo.py`:

```python
"""La regla de quién está en el campo (app/campo.py)."""
from app import campo


def _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, je_ids):
    """Crea el partido, guarda el plan del equipo 1 (obligatoriamente ANTES de
    iniciar) y lo pone en juego. je_ids son jugador_equipo_id de titulares."""
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": je, "posicion": "DEF", "orden": i}
                      for i, je in enumerate(je_ids)]})
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def _estado(db_session, pid, equipo_id=1):
    db = db_session()
    try:
        return campo.estado_campo(db, pid, equipo_id)
    finally:
        db.close()


def test_sin_plan_la_plantilla_entera_esta_en_campo(client, db_session, auth_admin,
                                                    auth_arbitro, arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    estado = _estado(db_session, pid)
    assert estado["hay_plan"] is False
    assert miembro_id in estado["en_campo"]


def test_con_plan_solo_los_titulares(client, db_session, auth_admin, auth_arbitro,
                                     auth_entrenador, agregar_miembro, arbitro_id, torneo_id):
    titular = agregar_miembro(auth_entrenador, 1, "Titular Campo", "titcampo@demo.com")
    banca = agregar_miembro(auth_entrenador, 1, "Banca Campo", "bancacampo@demo.com")
    pid = _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                    torneo_id, [titular["je_id"]])
    estado = _estado(db_session, pid)
    assert estado["hay_plan"] is True
    assert titular["jugador_id"] in estado["en_campo"]
    assert banca["jugador_id"] not in estado["en_campo"]


def test_expulsado_sale_del_campo(client, db_session, auth_admin, auth_arbitro,
                                  arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 30})
    estado = _estado(db_session, pid)
    assert miembro_id in estado["expulsados"]
    assert miembro_id not in estado["en_campo"]


def test_el_que_sale_de_cambio_deja_el_campo_y_el_que_entra_lo_ocupa(
        client, db_session, auth_admin, auth_arbitro, auth_entrenador,
        agregar_miembro, arbitro_id, torneo_id):
    sale = agregar_miembro(auth_entrenador, 1, "Sale Campo", "salecampo@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra Campo", "entracampo@demo.com")
    pid = _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                    torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    estado = _estado(db_session, pid)
    assert sale["jugador_id"] in estado["salidos"]
    assert sale["jugador_id"] not in estado["en_campo"]
    assert entra["jugador_id"] in estado["en_campo"]


def test_amarillas_se_cuentan_por_jugador(client, db_session, auth_admin, auth_arbitro,
                                          arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 20})
    estado = _estado(db_session, pid)
    assert estado["amarillas"].get(miembro_id) == 1
```

- [ ] **Step 2: Correrlos para ver que fallan**

Run: `cd api && .venv/bin/pytest tests/test_campo.py -v`
Expected: todos FALLAN en el import — `ModuleNotFoundError: No module named 'app.campo'`.

- [ ] **Step 3: Escribir el módulo**

Crear `api/app/campo.py`:

```python
"""
Quién está en el campo durante un partido.

    en_campo(equipo) = titulares del plan
                     − expulsados      (rojas > 0, directa o por doble amarilla)
                     − salidos         (salio == True)
                     + entrados        (entro == True)

Si el equipo NO registró plan, la plantilla entera cuenta como "en el campo"
(menos expulsados y salidos). No es una comodidad: sin plan el sistema no sabe
quién arrancó, y dejar al árbitro sin nadie elegible en mitad de un partido es
peor que no validar. Además es lo que sostiene los tests de eventos que ya
existen, que crean el partido sin registrar alineación. No lo quites.

Este módulo solo LEE: no hay tabla, columna ni migración nuevas.
"""
from sqlalchemy.orm import Session

from app import models
from app.eventos_resumen import resumen_por_jugador


def _plantilla_ids(db: Session, equipo_id: int) -> set[int]:
    """Ids de usuario de la plantilla del equipo."""
    equipo = db.get(models.Equipo, equipo_id)
    if equipo is None:
        return set()
    return {je.jugador_id for je in equipo.jugadores if je.jugador_id is not None}


def _plan_del_equipo(db: Session, partido_id: int, equipo_id: int) -> tuple[bool, set[int]]:
    """
    (hay_plan, ids de usuario titulares) del plan del entrenador.

    `hay_plan` sale de que EXISTA un plan con jugadores, no de que queden ids
    tras el filtro: `jugador_equipo.jugador_id` es nulable (un jugador de
    plantilla sin cuenta registrada), y un once entero de jugadores sin cuenta
    daría un conjunto vacío que se confundiría con "no hay alineación" y
    dejaría elegible a toda la banca.
    """
    plan = (
        db.query(models.AlineacionPlan)
        .filter_by(partido_id=partido_id, equipo_id=equipo_id)
        .first()
    )
    if plan is None or not plan.jugadores:
        return False, set()
    return True, {
        j.get("jugador_id")
        for j in plan.jugadores
        if j.get("jugador_id") is not None
    }


def estado_campo(db: Session, partido_id: int, equipo_id: int) -> dict:
    """
    Devuelve, para un equipo de un partido:

    - en_campo:   set[int]        ids de usuario que pueden recibir eventos
    - expulsados: set[int]        con al menos una roja
    - salidos:    set[int]        que salieron en un cambio
    - amarillas:  dict[int, int]  amarillas por jugador
    - hay_plan:   bool            False si el entrenador no registró alineación
    """
    resumen = resumen_por_jugador(db, partido_id)
    plantilla = _plantilla_ids(db, equipo_id)

    # El resumen es de TODO el partido; se acota a la plantilla del equipo.
    expulsados = {jid for jid, r in resumen.items() if r["rojas"] > 0} & plantilla
    salidos = {jid for jid, r in resumen.items() if r["salio"]} & plantilla
    entrados = {jid for jid, r in resumen.items() if r["entro"]} & plantilla

    hay_plan, titulares = _plan_del_equipo(db, partido_id, equipo_id)
    base = titulares if hay_plan else plantilla

    return {
        "en_campo": (base | entrados) - salidos - expulsados,
        "expulsados": expulsados,
        "salidos": salidos,
        # Acotadas a la plantilla como las demás claves: el resumen es de todo
        # el partido y el valor de retorno es "de un equipo".
        "amarillas": {jid: r["amarillas"] for jid, r in resumen.items() if jid in plantilla},
        "hay_plan": hay_plan,
    }
```

- [ ] **Step 4: Correr los tests**

Run: `cd api && .venv/bin/pytest tests/test_campo.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/app/campo.py api/tests/test_campo.py
git commit -m "feat(api): regla de quien esta en el campo durante el partido"
```

---

### Task 3: `registrar_evento` rechaza al que no está en el campo

**Files:**
- Modify: `api/app/routers/partidos.py` (import en la línea 20; dos helpers nuevos antes de `registrar_evento`, hoy en la 252-253; una llamada dentro de `registrar_evento` tras la comprobación del equipo, hoy en la 269-270)
- Test: `api/tests/test_arbitro_eventos.py` (tests nuevos al final)

**Interfaces:**
- Consumes: `campo.estado_campo(db, partido_id, equipo_id)` de la Tarea 2, con sus cinco claves.
- Produces: dos helpers de módulo, `_exigir_en_campo(estado: dict, jugador_id: int)` y `_validar_jugadores(estado: dict, datos: EventoCreate)`, y —dentro de `registrar_evento`— la variable local `estado`, que la **Tarea 4** reutiliza para la roja automática. No la borres ni la vuelvas a calcular: debe reflejar el estado **anterior** a este evento.

Tabla de la regla (del spec):

| Evento | `jugador_id` | `jugador_secundario_id` |
|---|---|---|
| `gol` | en el campo, **si viene** | asistente: en el campo, si viene |
| `tarjeta_amarilla` / `tarjeta_roja` | en el campo, **si viene** | — |
| `cambio` | el que sale: en el campo (**obligatorio**) | el que entra: no expulsado, y —**solo si hay plan**— no en el campo (**obligatorio**) |

- [ ] **Step 1: Escribir los tests que fallan**

Al final de `api/tests/test_arbitro_eventos.py`:

```python
def _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, je_ids):
    """Partido con plan del equipo 1 y en juego. El plan se guarda ANTES de
    iniciar: después de iniciar, PUT /plan responde 409."""
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id}).json()["id"]
    client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": je, "posicion": "DEF", "orden": i}
                      for i, je in enumerate(je_ids)]})
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def test_evento_sobre_expulsado_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                       torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Expulsado", "expulsado@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 40})
    assert r.status_code == 409
    assert "expulsado" in r.json()["detail"].lower()


def test_evento_sobre_jugador_que_ya_salio_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                  torneo_id, auth_entrenador, agregar_miembro):
    sale = agregar_miembro(auth_entrenador, 1, "Salio Ya", "salioya@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entro Ya", "entroya@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": sale["jugador_id"], "minuto": 70})
    assert r.status_code == 409


def test_evento_sobre_el_que_entro_de_cambio_se_acepta(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    sale = agregar_miembro(auth_entrenador, 1, "Sale Ok", "saleok@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra Ok", "entraok@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": entra["jugador_id"], "minuto": 70})
    assert r.status_code == 201


def test_cambio_con_el_que_sale_fuera_del_campo_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    titular = agregar_miembro(auth_entrenador, 1, "Titular Cbio", "titcbio@demo.com")
    banca_a = agregar_miembro(auth_entrenador, 1, "Banca A", "bancaa@demo.com")
    banca_b = agregar_miembro(auth_entrenador, 1, "Banca B", "bancab@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [titular["je_id"]])
    # banca_a no está en el campo: no puede "salir"
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": banca_a["jugador_id"],
        "jugador_secundario_id": banca_b["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_cambio_con_el_que_entra_ya_en_el_campo_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    uno = agregar_miembro(auth_entrenador, 1, "Titular Uno", "tituno@demo.com")
    dos = agregar_miembro(auth_entrenador, 1, "Titular Dos", "titdos@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [uno["je_id"], dos["je_id"]])
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": uno["jugador_id"],
        "jugador_secundario_id": dos["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_cambio_sin_los_dos_jugadores_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                             torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Solo Uno", "solouno@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_evento_sin_jugador_sigue_siendo_valido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    """El autogol atribuido solo al equipo no lleva jugador: no hay nada que validar."""
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "subtipo": "autogol", "minuto": 30})
    assert r.status_code == 201
```

- [ ] **Step 2: Correrlos para ver que fallan**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py -v`
Expected: los cuatro que esperan 409 FALLAN con 201; los que esperan 201 ya pasan.

- [ ] **Step 3: Importar `campo` en el router**

En `api/app/routers/partidos.py:20`, cambiar:

```python
from app import eventos_resumen, models
```

por:

```python
from app import campo, eventos_resumen, models
```

- [ ] **Step 4: Añadir los dos helpers antes de `registrar_evento`**

Insertar justo encima del decorador `@router.post("/{partido_id}/eventos", ...)` (hoy línea 252):

```python
def _exigir_en_campo(estado: dict, jugador_id: int):
    """409 con el motivo concreto si el jugador no puede recibir eventos."""
    if jugador_id in estado["en_campo"]:
        return
    if jugador_id in estado["expulsados"]:
        raise HTTPException(status_code=409, detail="El jugador está expulsado")
    if jugador_id in estado["salidos"]:
        raise HTTPException(status_code=409, detail="El jugador ya salió de cambio")
    raise HTTPException(status_code=409, detail="El jugador no está en el campo")


def _validar_jugadores(estado: dict, datos: EventoCreate):
    """
    Un evento puede no llevar jugador y eso es legal: el autogol atribuido solo
    al equipo va sin jugador_id, y la asistencia de un gol es opcional. Cuando
    el campo viene vacío no hay nada que comprobar. Solo el cambio exige los dos.
    """
    if datos.tipo == "cambio":
        if datos.jugador_id is None or datos.jugador_secundario_id is None:
            raise HTTPException(
                status_code=409,
                detail="Un cambio necesita el jugador que sale y el que entra",
            )
        _exigir_en_campo(estado, datos.jugador_id)          # el que sale
        entra = datos.jugador_secundario_id
        if entra in estado["expulsados"]:
            raise HTTPException(status_code=409, detail="El jugador que entra está expulsado")
        # Sin plan, la plantilla entera cuenta como "en el campo", así que esta
        # comprobación no se puede aplicar: dejaría todo cambio en 409.
        if estado["hay_plan"] and entra in estado["en_campo"]:
            raise HTTPException(status_code=409, detail="El jugador que entra ya está en el campo")
        return

    if datos.jugador_id is not None:
        _exigir_en_campo(estado, datos.jugador_id)
    if datos.tipo == "gol" and datos.jugador_secundario_id is not None:
        _exigir_en_campo(estado, datos.jugador_secundario_id)   # asistente
```

- [ ] **Step 5: Llamarlos desde `registrar_evento`**

Dentro de `registrar_evento`, justo después del bloque que comprueba el equipo (hoy `partidos.py:269-270`, el que lanza "El equipo no participa en este partido") y **antes** de construir `evento = models.EventoPartido(...)`, insertar:

```python
    estado = campo.estado_campo(db, partido_id, datos.equipo_id)
    _validar_jugadores(estado, datos)
```

- [ ] **Step 6: Correr los tests**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py tests/test_campo.py -v`
Expected: todo PASSED. En particular `test_cambio_con_jugador_que_entra` (el que ya existía, partido **sin plan**) sigue en 201: es lo que comprueba que el fallback está bien aplicado.

- [ ] **Step 7: Correr los otros archivos que registran eventos**

Run: `cd api && .venv/bin/pytest tests/test_partidos.py tests/test_estadisticas.py tests/test_eventos_resumen.py tests/test_jugador.py -q`
Expected: todo PASSED.

- [ ] **Step 8: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_arbitro_eventos.py
git commit -m "feat(api): rechazar eventos sobre jugadores que no estan en el campo"
```

---

### Task 4: La segunda amarilla expulsa

**Files:**
- Modify: `api/app/routers/partidos.py` (dentro de `registrar_evento`, tras el `db.add(evento)` que hoy está en la línea 282)
- Test: `api/tests/test_arbitro_eventos.py` (tests nuevos al final)

**Interfaces:**
- Consumes: la variable local `estado` que la Tarea 3 creó en `registrar_evento`, en concreto `estado["amarillas"]: dict[int, int]` — **amarillas anteriores a este evento**, porque `estado` se calculó antes de añadirlo.
- Produces: nada que consuman otras tareas. El endpoint sigue devolviendo la **amarilla**, no la roja.

La roja se crea como **evento aparte** (mismo partido, equipo, jugador y minuto) con `detalle="Doble amarilla"`. No hay que tocar distintivos, acta ni estadísticas: los cuatro consumidores ya cuentan `rojas` leyendo eventos.

- [ ] **Step 1: Escribir los tests que fallan**

Al final de `api/tests/test_arbitro_eventos.py`:

```python
def test_segunda_amarilla_genera_roja_automatica(client, auth_admin, auth_arbitro, arbitro_id,
                                                 torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Doble Amarilla", "doble@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 65})
    # El endpoint devuelve la amarilla, que es lo que se pidió crear
    assert r.status_code == 201 and r.json()["tipo"] == "tarjeta_amarilla"

    eventos = client.get(f"/partidos/{pid}/eventos", headers=auth_arbitro).json()
    rojas = [e for e in eventos
             if e["tipo"] == "tarjeta_roja" and e["jugador_id"] == m["jugador_id"]]
    assert len(rojas) == 1
    assert rojas[0]["minuto"] == 65
    assert "doble" in (rojas[0]["detalle"] or "").lower()


def test_una_sola_amarilla_no_genera_roja(client, auth_admin, auth_arbitro, arbitro_id,
                                          torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Una Amarilla", "unaamarilla@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    eventos = client.get(f"/partidos/{pid}/eventos", headers=auth_arbitro).json()
    assert not any(e["tipo"] == "tarjeta_roja" for e in eventos)


def test_tras_la_doble_amarilla_el_jugador_no_recibe_mas_eventos(
        client, auth_admin, auth_arbitro, arbitro_id, torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Fuera Ya", "fuueraya@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    for minuto in (20, 65):
        client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
            "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": minuto})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 80})
    assert r.status_code == 409
```

- [ ] **Step 2: Correrlos para ver que fallan**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py -k "amarilla" -v`
Expected: `test_segunda_amarilla_genera_roja_automatica` FALLA (0 rojas) y `test_tras_la_doble_amarilla...` FALLA (201 en vez de 409). `test_una_sola_amarilla_no_genera_roja` ya pasa.

- [ ] **Step 3: Crear la roja en la misma transacción**

En `registrar_evento`, justo después de `db.add(evento)` (hoy `partidos.py:282`) y antes del bloque `if datos.tipo == "gol":`, insertar:

```python
    # Segunda amarilla = expulsión. Se crea un evento de roja APARTE porque los
    # distintivos, el acta y las estadísticas ya cuentan rojas leyendo eventos:
    # marcar la amarilla obligaría a cambiar los cuatro consumidores.
    # `estado` se calculó antes de añadir esta amarilla, así que cuenta las previas.
    if (
        datos.tipo == "tarjeta_amarilla"
        and datos.jugador_id is not None
        and estado["amarillas"].get(datos.jugador_id, 0) >= 1
    ):
        db.add(models.EventoPartido(
            partido_id=partido_id,
            equipo_id=datos.equipo_id,
            jugador_id=datos.jugador_id,
            tipo="tarjeta_roja",
            minuto=datos.minuto,
            detalle="Doble amarilla",
        ))
```

- [ ] **Step 4: Correr los tests**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py tests/test_campo.py -v`
Expected: todo PASSED.

- [ ] **Step 5: Verificar que las estadísticas no se descuadran**

Run: `cd api && .venv/bin/pytest tests/test_estadisticas.py tests/test_jugador.py tests/test_partidos.py -q`
Expected: todo PASSED. (`test_estadisticas.py:27-28` da una amarilla y luego una roja al mismo jugador: la amarilla es la primera, así que no dispara la automática, y la roja entra porque aún no estaba expulsado.)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_arbitro_eventos.py
git commit -m "feat(api): la segunda amarilla expulsa al jugador"
```

---

### Task 5: `en_campo` y `expulsado` en la salida del plan

**Files:**
- Modify: `api/app/schemas.py:459-466` (`PlanItemOut`)
- Modify: `api/app/routers/partidos.py:443-483` (`_plan_a_salida`)
- Test: `api/tests/test_arbitro_eventos.py` (tests nuevos al final)

**Interfaces:**
- Consumes: `campo.estado_campo(db, partido_id, equipo_id)` de la Tarea 2.
- Produces: cada elemento de `jugadores` y de `suplentes` en `GET /partidos/{id}/plan?equipo_id=` lleva `en_campo: bool` y `expulsado: bool`. La Tarea 6 (móvil) lee exactamente esos dos nombres.

`_plan_a_salida` se llama también desde `guardar_plan`, con el partido en `programado` y sin eventos: ahí `en_campo` sale `True` para los titulares y `False` para la banca, que es lo correcto.

- [ ] **Step 1: Escribir los tests que fallan**

Al final de `api/tests/test_arbitro_eventos.py`:

```python
def test_plan_marca_quien_esta_en_el_campo(client, auth_admin, auth_arbitro, arbitro_id,
                                           torneo_id, auth_entrenador, agregar_miembro):
    titular = agregar_miembro(auth_entrenador, 1, "En Campo", "encampo@demo.com")
    banca = agregar_miembro(auth_entrenador, 1, "En Banca", "enbanca@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [titular["je_id"]])
    plan = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_arbitro).json()

    t = next(j for j in plan["jugadores"] if j["jugador_id"] == titular["jugador_id"])
    b = next(s for s in plan["suplentes"] if s["jugador_id"] == banca["jugador_id"])
    assert t["en_campo"] is True and t["expulsado"] is False
    assert b["en_campo"] is False and b["expulsado"] is False


def test_plan_marca_al_expulsado(client, auth_admin, auth_arbitro, arbitro_id,
                                 torneo_id, auth_entrenador, agregar_miembro):
    titular = agregar_miembro(auth_entrenador, 1, "Va Fuera", "vafuera@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [titular["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": titular["jugador_id"], "minuto": 30})
    plan = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_arbitro).json()
    t = next(j for j in plan["jugadores"] if j["jugador_id"] == titular["jugador_id"])
    assert t["en_campo"] is False and t["expulsado"] is True


def test_plan_tras_un_cambio_intercambia_las_banderas(client, auth_admin, auth_arbitro, arbitro_id,
                                                      torneo_id, auth_entrenador, agregar_miembro):
    sale = agregar_miembro(auth_entrenador, 1, "Sale Plan", "saleplan@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra Plan", "entraplan@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    plan = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_arbitro).json()
    s = next(j for j in plan["jugadores"] if j["jugador_id"] == sale["jugador_id"])
    e = next(j for j in plan["suplentes"] if j["jugador_id"] == entra["jugador_id"])
    assert s["en_campo"] is False
    assert e["en_campo"] is True
```

- [ ] **Step 2: Correrlos para ver que fallan**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py -k "plan_marca or plan_tras" -v`
Expected: FALLAN con `KeyError: 'en_campo'`.

- [ ] **Step 3: Añadir los campos al esquema**

En `api/app/schemas.py`, dentro de `class PlanItemOut` (hoy línea 459), después de `tiene_foto`:

```python
    tiene_foto: bool = False        # el panel web solo pinta <img> si es True
    en_campo: bool = False          # puede recibir eventos ahora mismo
    expulsado: bool = False         # tiene al menos una roja en este partido
```

- [ ] **Step 4: Rellenarlos en `_plan_a_salida`**

En `api/app/routers/partidos.py`, dentro de `_plan_a_salida`, sustituir el helper local `_con_foto` (hoy líneas 474-475) por:

```python
    estado = campo.estado_campo(db, partido_id, equipo_id)

    def _enriquecer(d):
        jid = d.get("jugador_id")
        return {
            **d,
            "tiene_foto": jid in con_foto,
            "en_campo": jid is not None and jid in estado["en_campo"],
            "expulsado": jid is not None and jid in estado["expulsados"],
        }
```

y en el `return PlanOut(...)` de la misma función (hoy líneas 481-482) cambiar las dos llamadas:

```python
        jugadores=[_enriquecer(j) for j in titulares],
        suplentes=[_enriquecer(s) for s in suplentes],
```

- [ ] **Step 5: Correr los tests**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_eventos.py tests/test_campo.py -v`
Expected: todo PASSED, incluido `test_plan_incluye_suplentes`, que ya existía.

- [ ] **Step 6: Correr la suite completa**

Run: `cd api && .venv/bin/pytest -q`
Expected: 0 failed. ⚠️ Tarda **~12,5 min**: no la interrumpas creyendo que se colgó. El total debe rondar los **250** tests (233 de base + ~17 nuevos).

- [ ] **Step 7: Commit**

```bash
git add api/app/schemas.py api/app/routers/partidos.py api/tests/test_arbitro_eventos.py
git commit -m "feat(api): el plan expone quien esta en el campo y quien esta expulsado"
```

---

### Task 6: La app del árbitro filtra por las banderas y exige el minuto

**Files:**
- Modify: `mobile/src/screens/referee/RefEventScreen.js` (líneas 88-95, 97-119 y 136-144)

**Interfaces:**
- Consumes: `en_campo: bool` y `expulsado: bool` en cada elemento de `jugadores` y `suplentes` de `GET /partidos/{id}/plan?equipo_id=` (Tarea 5).
- Produces: nada. Es la punta del cambio.

**El cliente no recalcula la regla**: filtra por las banderas que da el servidor. La barrera real sigue siendo el 409. No hay llamadas nuevas: la pantalla ya pedía el plan de cada equipo (líneas 65-75).

Sin plan del entrenador, el servidor marca `en_campo` a toda la plantilla, así que la lista de "quién entra" quedaría vacía y el árbitro no podría registrar un cambio. Por eso el cliente detecta ese caso con `titulares.length === 0` —el mismo dato, sin campo nuevo— y en él ofrece la banca entera menos los expulsados, que es lo que el servidor acepta.

En este repo no hay tests de la app: se verifica con `npm run verificar` y en dispositivo.

- [ ] **Step 1: Sustituir el cálculo del pool**

En `mobile/src/screens/referee/RefEventScreen.js`, reemplazar las líneas 88-95 (desde `const datosEquipo` hasta el cierre del `useMemo` de `asistentes`) por:

```js
  const datosEquipo = planes[equipoSel] || { titulares: [], suplentes: [] };
  const plantilla = useMemo(
    () => [...datosEquipo.titulares, ...datosEquipo.suplentes],
    [datosEquipo]
  );
  // Sin alineación del entrenador el servidor marca en_campo a toda la plantilla:
  // ahí la banca sigue siendo la lista de quién puede entrar.
  const sinPlan = datosEquipo.titulares.length === 0;

  // El servidor decide quién está en el campo (titulares − expulsados − salidos
  // + entrados). Aquí solo se lee la bandera: si la regla cambia, cambia allá.
  const enCancha = useMemo(() => plantilla.filter((j) => j.en_campo), [plantilla]);

  const asistentes = useMemo(
    () => enCancha.filter((j) => j.jugador_id !== principal),
    [enCancha, principal]
  );

  // Quién puede entrar en un cambio: los que no están en el campo y no están
  // expulsados. Sin plan, la banca entera menos los expulsados.
  const entrantes = useMemo(() => {
    const base = sinPlan ? datosEquipo.suplentes : plantilla.filter((j) => !j.en_campo);
    return base.filter((j) => !j.expulsado && j.jugador_id !== principal);
  }, [plantilla, datosEquipo, sinPlan, principal]);
```

- [ ] **Step 2: Exigir el minuto antes de enviar**

En la misma pantalla, dentro de `confirmar()`, reemplazar el bloque de las líneas 104-110:

```js
    setGuardando(true);
    const cuerpo = { tipo, equipo_id: equipoSel };
    if (principal != null) cuerpo.jugador_id = principal;
    if (secundario != null) cuerpo.jugador_secundario_id = secundario;
    if (esGol) cuerpo.subtipo = subtipo;
    const m = parseInt(minuto, 10);
    if (!Number.isNaN(m)) cuerpo.minuto = m;
```

por:

```js
    // Antes se omitía el minuto en silencio si el campo estaba vacío: así se
    // colaban eventos sin saber cuándo ocurrieron. Ahora el API lo exige (422).
    const m = parseInt(minuto, 10);
    if (Number.isNaN(m) || m < 0 || m > 130) {
      Alert.alert("Falta el minuto", "Escribe el minuto del partido (entre 0 y 130)."); return;
    }
    setGuardando(true);
    const cuerpo = { tipo, equipo_id: equipoSel, minuto: m };
    if (principal != null) cuerpo.jugador_id = principal;
    if (secundario != null) cuerpo.jugador_secundario_id = secundario;
    if (esGol) cuerpo.subtipo = subtipo;
```

- [ ] **Step 3: Usar las listas nuevas en el render del cambio**

Reemplazar las líneas 136-144 (el bloque `{esCambio ? (…)`) por:

```js
      {esCambio ? (
        <>
          <Text style={ls.sectionTitle}>Jugador que sale (en cancha)</Text>
          <ListaJugadores jugadores={enCancha} seleccion={principal} onSelect={setPrincipal}
            vacio="No hay jugadores en el campo." />
          <Text style={ls.sectionTitle}>Jugador que entra (banca)</Text>
          <ListaJugadores jugadores={entrantes} seleccion={secundario} onSelect={setSecundario}
            vacio="No hay suplentes disponibles." />
        </>
      ) : (
```

(La rama `: (` y todo lo que sigue —anotador, asistencia, minuto, tipo de gol— se queda igual: ya usa `enCancha` y `asistentes`, que ahora salen de las banderas.)

- [ ] **Step 4: Verificar la sintaxis**

Run: `cd mobile && npm run verificar`
Expected: OK, sin errores. ⚠️ **No uses `npx babel`**: resuelve al paquete `babel` v6 deprecado del caché de npx y hace fallar archivos válidos.

- [ ] **Step 5: Comprobar que no quedó ningún uso viejo**

Run: `cd mobile && grep -n "datosEquipo.titulares" src/screens/referee/RefEventScreen.js`
Expected: una sola línea, la del cálculo de `sinPlan`. Si aparece dentro del render, quedó un uso sin migrar.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/referee/RefEventScreen.js
git commit -m "feat(movil): el arbitro solo ve a quien puede recibir el evento y el minuto es obligatorio"
```

---

## Verificación final

- [ ] Suite completa en verde: `cd api && .venv/bin/pytest -q` → 0 failed, ~250 tests (base 233). **Tarda ~12,5 min.**
- [ ] App sin errores de sintaxis: `cd mobile && npm run verificar`.
- [ ] `git log --oneline` muestra los 6 commits de las tareas sobre los 2 del spec.
- [ ] **Validación en dispositivo** (backend local levantado, `docker compose up -d`, migrado y sembrado):
  - Dos amarillas al mismo jugador → al volver a la pantalla en vivo aparece la roja sola, y ese jugador ya no sale en las listas.
  - Un cambio: el que sale desaparece de las listas y el que entra empieza a salir.
  - Confirmar un evento con el minuto vacío → avisa y no envía.
  - Un partido **sin alineación cargada** por el entrenador → el árbitro sigue pudiendo registrar goles, tarjetas y cambios.

## Correcciones salidas de la revisión final

La revisión de toda la rama encontró **dos huecos de este plan** —no de la implementación—, ambos verificados en vivo contra la API. Se corrigieron antes de cerrar, con sus tests:

1. **Un cambio podía meter de vuelta al que ya había salido.** `_validar_jugadores` comprobaba que el que entra no estuviera expulsado y (con plan) que no estuviera ya en el campo, pero no que **ya se hubiera ido**. Como `salio` es un pestillo y `en_campo` resta `salidos` siempre, el reingresado quedaba fuera para siempre: el equipo pasaba de dos jugadores en el campo a uno, y ninguno de los dos podía recibir nada más. Era alcanzable desde la app —la lista de "quién entra" ofrece justo "no en campo y no expulsado", que es como se ve un sustituido— y era una **regresión**: antes de esta rama ese jugador sí podía recibir eventos. Se rechaza con 409.
2. **Borrar la segunda amarilla dejaba huérfana la roja automática.** Las dos se crean en una transacción pero se deshacían en dos, así que corregir una amarilla mal registrada dejaba al jugador con una roja que nunca recibió y expulsado el resto del partido, además de ensuciar el acta y el ranking de tarjetas. `eliminar_evento` borra ahora la roja automática cuando al jugador le quedan menos de dos amarillas. Una roja **directa** no se toca.

## Deuda menor anotada (revisada y aparcada a propósito)

Nada de esto bloquea el merge; la revisión final las triró una por una.

- **`eliminar_evento` acota la limpieza por partido y jugador, no por equipo.** Solo importaría si el mismo `usuario.id` estuviera en las plantillas de los dos equipos del mismo partido, cosa que ningún flujo actual crea.
- **`campo.py` devuelve `hay_plan=True` para un plan con `jugadores` vacío.** Hoy es inalcanzable (`guardar_plan` rechaza la alineación vacía con 400); si pasara, el equipo se quedaría con `en_campo` vacío. Tratar la lista vacía como "sin plan" sería más seguro.
- **El `sinPlan` del cliente no es idéntico al `hay_plan` del servidor**: el móvil mira `titulares.length === 0` sobre una lista ya filtrada a los que tienen cuenta. Divergen solo si ningún titular tiene cuenta. Se cerraría exponiendo también `salio` en `PlanItemOut`, que además haría que la lista de "quién entra" coincidiera exactamente con la regla del servidor en vez de aproximarla.
- **`RefEventScreen.js` sigue diciendo "El entrenador no cargó la alineación"** cuando la lista de jugadores sale vacía, pero ahora también puede vaciarse por expulsiones y cambios.
- **Tests**: los dos POST de amarilla del test transversal de `test_campo.py` no comprueban su `status_code`; ese archivo usa `CryptContext` directo en vez de `app.security.hash_password` y tiene un fallback a `rol_id=3` que en el seed es `arbitro` (camino muerto). Falta un test de `tarjeta_amarilla` sin `jugador_id` (la rama no-op del guard de la roja automática).
- **~840 warnings** en la suite completa, todos preexistentes (passlib/jose/Pydantic). Triarlos es su propia tarea.
- **El spec dice mal un riesgo**: afirma que al desplegar, un jugador con dos amarillas previas y sin roja "quedará marcado como expulsado". No es así — `expulsados` exige `rojas > 0`, así que sigue siendo elegible; solo su **siguiente** amarilla dispara la roja automática. El comportamiento real es más suave que el documentado.

## Qué queda fuera, a propósito

- **Notificaciones para entrenador y árbitro**: spec aparte, no escrito.
- **Corrección de datos históricos**: los partidos ya jugados con dos amarillas y sin roja se quedan así; el evento `id = 12` sin minuto también.
- **`NOT NULL` en `eventos_partido.minuto`**: decisión explícita del usuario.
- **Límite de jugadores por equipo** (jugar con diez tras una expulsión): el sistema no lleva esa cuenta y no se pidió.
