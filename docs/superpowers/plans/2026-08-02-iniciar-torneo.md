# Iniciar torneo (calendario + árbitros) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Botón "Iniciar torneo" en el panel que genera el calendario (liga ida/vuelta o eliminación con byes a potencia de 2) y asignación de árbitros sin choques de fecha/hora.

**Architecture:** Generadores **puros** en un módulo nuevo `api/app/calendario.py` (probados sin BD); los endpoints (`iniciar`, `siguiente-ronda` en el router de torneos; `arbitros-disponibles` y las reglas de choque/empate en el de partidos) solo orquestan. El panel Flask agrega 3 rutas y toca 4 plantillas. Una migración: columna `partidos.jornada`.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest (API); Flask/Jinja (panel). Spec: `docs/superpowers/specs/2026-08-02-iniciar-torneo-design.md`.

## Global Constraints

- Rama: `feat/iniciar-torneo` (ya creada, spec commiteado). Commits con el trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Tests desde `api/` con el venv del proyecto: `cd api && .venv/bin/pytest ...`. La suite completa tarda ~7 min — solo correrla en la Task 7.
- Código, comentarios y mensajes de error en español (estilo del repo).
- Tipos canónicos de torneo tras normalizar: `liga` y `eliminacion directa`. Estados de torneo: `programado/en_curso/finalizado`; de partido: `programado/en_juego/finalizado`.
- Regla de choque de árbitro: MISMA `fecha_hora` exacta y partido no-`finalizado` (sin ventanas de traslape).
- Al iniciar: notificación ÚNICA por entrenador (no por partido). Fechas: `primera_fecha`+`hora_base` como UTC, jornadas semanales, partidos de la misma jornada escalonados +2 h, canchas de la sede del torneo rotando.
- Panel: sin `<script>` inline (CSP); seguir los patrones existentes (`api_get/api_post/api_put`, `_detalle_error`, `_sesion_expirada`, flash).

---

### Task 1: Columna `jornada` en partidos (modelo + migración + salida)

**Files:**
- Modify: `api/app/models.py` (clase `Partido`, junto a `estado`, ~línea 222)
- Modify: `api/app/schemas.py` (clase `PartidoOut`, ~línea 169)
- Create: `api/migrations/versions/20260802_2340_jornada_en_partidos.py`
- Test: `api/tests/test_torneo_iniciar.py` (nuevo)

**Interfaces:**
- Produces: `models.Partido.jornada` (Integer, nullable) y `PartidoOut.jornada: int | None` — las Tasks 3-4 escriben `jornada` al crear partidos.

- [ ] **Step 1: Test que falla**

Crear `api/tests/test_torneo_iniciar.py`:

```python
"""Iniciar torneo: columna jornada, generación de calendario y rondas."""


def test_partido_expone_jornada(client, db_session, auth_admin):
    from app import models
    db = db_session()
    torneo = models.Torneo(nombre="T Jornada", sede_id=1, tipo="liga")
    db.add(torneo)
    db.commit()
    p = models.Partido(torneo_id=torneo.id, equipo_local_id=1,
                       equipo_visitante_id=2, estado="programado", jornada=3)
    db.add(p)
    db.commit()
    pid = p.id
    db.close()

    r = client.get(f"/partidos/{pid}", headers=auth_admin)
    assert r.status_code == 200 and r.json()["jornada"] == 3
```

- [ ] **Step 2: Verificar que falla**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py -v`
Expected: FAIL con `TypeError: 'jornada' is an invalid keyword argument for Partido`

- [ ] **Step 3: Implementar**

En `api/app/models.py`, dentro de `class Partido`, después de la línea de `estado`:

```python
    # Nº de jornada (liga) o de ronda (eliminación). NULL en partidos creados
    # a mano o anteriores a esta columna.
    jornada = Column(Integer)
```

En `api/app/schemas.py`, dentro de `PartidoOut`, después de `estado: str`:

```python
    jornada: int | None = None
```

Crear `api/migrations/versions/20260802_2340_jornada_en_partidos.py`:

```python
"""jornada en partidos

Revision ID: e5f6a7b8c9d0
Revises: d3f4a5b6c7e8
Create Date: 2026-08-02 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d3f4a5b6c7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("partidos", sa.Column("jornada", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("partidos", "jornada")
```

- [ ] **Step 4: Verificar que pasa (incluye la guardia de migraciones)**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py tests/test_migraciones_env.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/models.py api/app/schemas.py api/migrations/versions/20260802_2340_jornada_en_partidos.py api/tests/test_torneo_iniciar.py
git commit -m "feat(api): columna jornada en partidos (nro de jornada o ronda)"
```

---

### Task 2: Generadores puros de calendario (`app/calendario.py`)

**Files:**
- Create: `api/app/calendario.py`
- Test: `api/tests/test_calendario.py` (nuevo)

**Interfaces:**
- Produces (los consumen las Tasks 3-5):
  - `normalizar_tipo(tipo: str | None) -> str | None` — minúsculas, sin acentos, espacios colapsados.
  - `siguiente_potencia_de_2(n: int) -> int`
  - `generar_liga(equipos: list[int]) -> list[list[tuple[int, int]]]` — jornadas de ida y vuelta; cada tupla es `(local_id, visitante_id)`.
  - `generar_ronda_eliminacion(equipos: list[int], rng: random.Random) -> tuple[list[int], list[tuple[int, int]]]` — `(byes, parejas)`.

- [ ] **Step 1: Tests que fallan**

Crear `api/tests/test_calendario.py`:

```python
"""Generadores puros de calendario: liga (ida/vuelta) y eliminación (byes)."""
import random
from collections import Counter

from app import calendario


# ---------- normalizar_tipo ----------
def test_normalizar_tipo():
    assert calendario.normalizar_tipo("Liga") == "liga"
    assert calendario.normalizar_tipo("  Eliminación   Directa ") == "eliminacion directa"
    assert calendario.normalizar_tipo(None) is None
    assert calendario.normalizar_tipo("copa") == "copa"


# ---------- siguiente_potencia_de_2 ----------
def test_siguiente_potencia_de_2():
    assert calendario.siguiente_potencia_de_2(2) == 2
    assert calendario.siguiente_potencia_de_2(3) == 4
    assert calendario.siguiente_potencia_de_2(6) == 8
    assert calendario.siguiente_potencia_de_2(8) == 8


# ---------- liga ----------
def _pares(jornadas):
    return [frozenset(p) for j in jornadas for p in j]


def test_liga_par_ida_y_vuelta():
    jornadas = calendario.generar_liga([1, 2, 3, 4])
    assert len(jornadas) == 6                      # 2(n-1)
    assert all(len(j) == 2 for j in jornadas)      # n/2 partidos por jornada
    conteo = Counter(_pares(jornadas))
    assert len(conteo) == 6 and all(v == 2 for v in conteo.values())


def test_liga_localia_invertida_en_la_vuelta():
    jornadas = calendario.generar_liga([1, 2, 3, 4])
    ida, vuelta = jornadas[:3], jornadas[3:]
    partidos_ida = {p for j in ida for p in j}
    partidos_vuelta = {p for j in vuelta for p in j}
    assert partidos_vuelta == {(v, l) for (l, v) in partidos_ida}


def test_liga_impar_descansa():
    jornadas = calendario.generar_liga([1, 2, 3])
    assert len(jornadas) == 6                      # con fantasma: 2n
    assert all(len(j) == 1 for j in jornadas)      # uno descansa por jornada
    conteo = Counter(_pares(jornadas))
    assert len(conteo) == 3 and all(v == 2 for v in conteo.values())


def test_liga_nadie_juega_dos_veces_en_una_jornada():
    for j in calendario.generar_liga([1, 2, 3, 4, 5, 6]):
        vistos = [e for p in j for e in p]
        assert len(vistos) == len(set(vistos))


# ---------- eliminación ----------
def test_eliminacion_seis_equipos_dos_byes():
    byes, parejas = calendario.generar_ronda_eliminacion(
        [1, 2, 3, 4, 5, 6], random.Random(42))
    assert len(byes) == 2 and len(parejas) == 2
    usados = list(byes) + [e for p in parejas for e in p]
    assert sorted(usados) == [1, 2, 3, 4, 5, 6]    # todos, sin repetir


def test_eliminacion_potencia_exacta_sin_byes():
    byes, parejas = calendario.generar_ronda_eliminacion(
        [1, 2, 3, 4], random.Random(1))
    assert byes == [] and len(parejas) == 2


def test_eliminacion_dos_equipos_final_directa():
    byes, parejas = calendario.generar_ronda_eliminacion([1, 2], random.Random(1))
    assert byes == [] and len(parejas) == 1


def test_eliminacion_es_aleatoria_pero_reproducible():
    a = calendario.generar_ronda_eliminacion([1, 2, 3, 4, 5, 6], random.Random(7))
    b = calendario.generar_ronda_eliminacion([1, 2, 3, 4, 5, 6], random.Random(7))
    assert a == b
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_calendario.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.calendario'`

- [ ] **Step 3: Implementar**

Crear `api/app/calendario.py`:

```python
"""Generadores puros de calendario. Sin BD: reciben ids, devuelven cruces.

- Liga: round-robin por el método del círculo, ida y vuelta (la vuelta espeja
  cada jornada con la localía invertida).
- Eliminación directa: para que las llaves cuadren hasta la final, el número
  de participantes de la ronda 2 debe ser potencia de 2. Con n inscritos se
  dan `siguiente_potencia_de_2(n) - n` byes al azar (solo en la ronda 1); el
  resto se baraja y se empareja.
"""
import random
import unicodedata


def normalizar_tipo(tipo: str | None) -> str | None:
    """'  Eliminación   Directa ' -> 'eliminacion directa'."""
    if not tipo:
        return None
    plano = unicodedata.normalize("NFD", tipo)
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return " ".join(plano.lower().split())


def siguiente_potencia_de_2(n: int) -> int:
    return 1 if n <= 1 else 1 << (n - 1).bit_length()


def generar_liga(equipos: list[int]) -> list[list[tuple[int, int]]]:
    """Jornadas de ida + vuelta. Impar: se añade un fantasma (None) y quien
    le toca descansa esa jornada."""
    rueda = list(equipos)
    if len(rueda) % 2 == 1:
        rueda.append(None)
    n = len(rueda)
    ida = []
    for _ in range(n - 1):
        jornada = []
        for k in range(n // 2):
            a, b = rueda[k], rueda[n - 1 - k]
            if a is not None and b is not None:
                jornada.append((a, b))
        ida.append(jornada)
        # rota todos menos el primero
        rueda = [rueda[0]] + [rueda[-1]] + rueda[1:-1]
    vuelta = [[(v, l) for (l, v) in jornada] for jornada in ida]
    return ida + vuelta


def generar_ronda_eliminacion(
    equipos: list[int], rng: random.Random
) -> tuple[list[int], list[tuple[int, int]]]:
    """(byes, parejas). El rng se inyecta para poder probar determinista."""
    ids = list(equipos)
    rng.shuffle(ids)
    n_byes = siguiente_potencia_de_2(len(ids)) - len(ids)
    byes, juegan = ids[:n_byes], ids[n_byes:]
    parejas = [(juegan[i], juegan[i + 1]) for i in range(0, len(juegan), 2)]
    return byes, parejas
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd api && .venv/bin/pytest tests/test_calendario.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/calendario.py api/tests/test_calendario.py
git commit -m "feat(api): generadores de calendario (liga ida/vuelta y eliminacion con byes)"
```

---

### Task 3: `POST /torneos/{id}/iniciar`

**Files:**
- Modify: `api/app/schemas.py` (junto a `TorneoOut`, ~línea 96)
- Modify: `api/app/routers/torneos.py` (imports + endpoint nuevo al final)
- Test: `api/tests/test_torneo_iniciar.py` (agregar)

**Interfaces:**
- Consumes: `calendario.normalizar_tipo`, `calendario.generar_liga`, `calendario.generar_ronda_eliminacion` (Task 2); `models.Partido.jornada` (Task 1); `notificaciones_service.crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)` (existente).
- Produces: respuesta `{"torneo_id", "estado", "partidos_creados"}`; partidos con `jornada` desde 1. La Task 4 asume esta numeración.

- [ ] **Step 1: Tests que fallan**

Agregar a `api/tests/test_torneo_iniciar.py`:

```python
# ---------- helpers ----------
def _torneo(client, auth_admin, tipo="Liga", **over):
    body = {"nombre": f"Torneo {tipo}", "sede_id": 1, "tipo": tipo}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def _inscribir_aceptados(db_session, torneo_id, equipo_ids):
    from app import models
    db = db_session()
    for eid in equipo_ids:
        db.add(models.Inscripcion(torneo_id=torneo_id, equipo_id=eid, estado="aceptada"))
    db.commit()
    db.close()


def _equipos_extra(db_session, n):
    """Crea n equipos más (el seed trae 2, del mismo entrenador)."""
    from app import models
    db = db_session()
    base = db.query(models.Equipo).first()
    nuevos = [models.Equipo(entrenador_id=base.entrenador_id, nombre=f"Extra {i}")
              for i in range(n)]
    db.add_all(nuevos)
    db.commit()
    ids = [e.id for e in nuevos]
    db.close()
    return ids


# ---------- iniciar: liga ----------
def test_iniciar_liga_dos_equipos(client, db_session, auth_admin):
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])

    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 200, r.text
    assert r.json()["partidos_creados"] == 2      # ida y vuelta
    assert r.json()["estado"] == "en_curso"

    partidos = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()
    assert sorted(p["jornada"] for p in partidos) == [1, 2]
    ida, vuelta = sorted(partidos, key=lambda p: p["jornada"])
    # localía invertida entre ida y vuelta
    assert (ida["equipo_local_id"], ida["equipo_visitante_id"]) == \
           (vuelta["equipo_visitante_id"], vuelta["equipo_local_id"])
    # jornadas separadas una semana
    assert ida["fecha_hora"][:10] == "2026-09-05"
    assert vuelta["fecha_hora"][:10] == "2026-09-12"


def test_iniciar_valida_estado_tipo_e_inscripciones(client, db_session, auth_admin):
    # tipo no reconocido
    tid = _torneo(client, auth_admin, tipo="Copa rara")
    _inscribir_aceptados(db_session, tid, [1, 2])
    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 400

    # menos de 2 aceptadas
    tid2 = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid2, [1])
    r = client.post(f"/torneos/{tid2}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 400

    # ya en curso -> 409
    tid3 = _torneo(client, auth_admin, tipo="Liga", estado="en_curso")
    r = client.post(f"/torneos/{tid3}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 409


def test_iniciar_eliminacion_seis_equipos(client, db_session, auth_admin):
    extras = _equipos_extra(db_session, 4)
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    _inscribir_aceptados(db_session, tid, [1, 2] + extras)

    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "10:00"})
    assert r.status_code == 200, r.text
    # 6 equipos -> 2 byes y 2 partidos de ronda 1 (regla de potencia de 2)
    assert r.json()["partidos_creados"] == 2
    partidos = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()
    assert all(p["jornada"] == 1 for p in partidos)
    # escalonados +2h el mismo día
    horas = sorted(p["fecha_hora"][11:16] for p in partidos)
    assert horas == ["10:00", "12:00"]


def test_iniciar_notifica_una_vez_por_entrenador(client, db_session, auth_admin):
    from app import models
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])   # mismo entrenador (seed)
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    db = db_session()
    avisos = (db.query(models.Notificacion)
              .filter(models.Notificacion.titulo == "Torneo iniciado").count())
    db.close()
    assert avisos == 1   # dos equipos, un entrenador -> UNA notificación
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py -v`
Expected: los 4 nuevos FAIL con 404/405 (`POST /torneos/{id}/iniciar` no existe); `test_partido_expone_jornada` sigue PASS.

- [ ] **Step 3: Implementar**

En `api/app/schemas.py`, después de `TorneoOut` (la línea `from datetime import date, time` ya existe más abajo, ~101; moverla arriba de este bloque si hace falta):

```python
class TorneoIniciar(BaseModel):
    primera_fecha: date
    hora_base: time


class TorneoSiguienteRonda(BaseModel):
    fecha: date
    hora_base: time
```

En `api/app/routers/torneos.py`: ampliar imports y agregar el endpoint al final:

```python
import random
from datetime import datetime, timedelta, timezone

from app import calendario
from app.schemas import TorneoIniciar, TorneoSiguienteRonda
```

(integrarlos en los imports existentes, no duplicar líneas)

```python
TIPOS_INICIABLES = ("liga", "eliminacion directa")


def _canchas_de_la_sede(db: Session, torneo: models.Torneo) -> list[int]:
    return [c.id for c in (db.query(models.Cancha)
                           .filter_by(sede_id=torneo.sede_id)
                           .order_by(models.Cancha.id).all())]


def _crear_partidos(db, torneo, jornadas, base, canchas, primera_jornada=1):
    """Inserta las jornadas; semanas consecutivas, +2h por partido de jornada."""
    creados = 0
    for nj, jornada in enumerate(jornadas):
        for np_, (local, visita) in enumerate(jornada):
            db.add(models.Partido(
                torneo_id=torneo.id,
                equipo_local_id=local, equipo_visitante_id=visita,
                cancha_id=canchas[creados % len(canchas)] if canchas else None,
                fecha_hora=base + timedelta(weeks=nj, hours=2 * np_),
                estado="programado", jornada=primera_jornada + nj,
            ))
            creados += 1
    return creados


@router.post("/{torneo_id}/iniciar")
def iniciar_torneo(
    torneo_id: int,
    datos: TorneoIniciar,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    if torneo.estado != "programado":
        raise HTTPException(status_code=409, detail="Solo se puede iniciar un torneo programado")
    tipo = calendario.normalizar_tipo(torneo.tipo)
    if tipo not in TIPOS_INICIABLES:
        raise HTTPException(
            status_code=400,
            detail="El tipo del torneo debe ser 'liga' o 'eliminación directa'")
    inscripciones = (db.query(models.Inscripcion)
                     .filter_by(torneo_id=torneo.id, estado="aceptada").all())
    equipos = [i.equipo_id for i in inscripciones]
    if len(equipos) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se necesitan al menos 2 equipos con inscripción aceptada")

    base = datetime.combine(datos.primera_fecha, datos.hora_base, tzinfo=timezone.utc)
    if tipo == "liga":
        jornadas = calendario.generar_liga(equipos)
    else:
        # Los byes no se guardan: se derivan (aceptados que no juegan la ronda 1).
        _byes, parejas = calendario.generar_ronda_eliminacion(equipos, random.Random())
        jornadas = [parejas]

    creados = _crear_partidos(db, torneo, jornadas, base, _canchas_de_la_sede(db, torneo))
    torneo.estado = "en_curso"
    db.commit()

    # UNA notificación por entrenador (no por partido: serían cientos).
    entrenadores = {db.get(models.Equipo, eid).entrenador_id for eid in equipos}
    for uid in entrenadores:
        notificaciones_service.crear_notificacion(
            db, uid, "Torneo iniciado",
            f"{torneo.nombre} comenzó: revisa tu calendario.", background_tasks)
    db.commit()
    return {"torneo_id": torneo.id, "estado": torneo.estado, "partidos_creados": creados}
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py tests/test_calendario.py -v`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/schemas.py api/app/routers/torneos.py api/tests/test_torneo_iniciar.py
git commit -m "feat(api): POST /torneos/{id}/iniciar genera el calendario"
```

---

### Task 4: `POST /torneos/{id}/siguiente-ronda`

**Files:**
- Modify: `api/app/routers/torneos.py` (endpoint nuevo, debajo de `iniciar_torneo`)
- Test: `api/tests/test_torneo_iniciar.py` (agregar)

**Interfaces:**
- Consumes: `TorneoSiguienteRonda` (Task 3), `_crear_partidos`/`_canchas_de_la_sede` (Task 3), `calendario.generar_ronda_eliminacion` (Task 2).
- Produces: `{"ronda", "partidos_creados", "estado"}` o, con campeón, `{"campeon_id", "campeon", "estado": "finalizado", "partidos_creados": 0}`.

- [ ] **Step 1: Tests que fallan**

Agregar a `api/tests/test_torneo_iniciar.py`:

```python
def _finalizar_ronda(db_session, torneo_id, ronda):
    """Marca finalizados los partidos de la ronda con marcadores SIN empate."""
    from app import models
    db = db_session()
    partidos = (db.query(models.Partido)
                .filter_by(torneo_id=torneo_id, jornada=ronda).all())
    for i, p in enumerate(partidos):
        p.goles_local, p.goles_visitante = (2, 1) if i % 2 == 0 else (0, 3)
        p.estado = "finalizado"
    db.commit()
    db.close()
    return len(partidos)


def test_siguiente_ronda_flujo_completo_seis_equipos(client, db_session, auth_admin):
    extras = _equipos_extra(db_session, 4)
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    _inscribir_aceptados(db_session, tid, [1, 2] + extras)
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "10:00"})

    # ronda 1 incompleta -> 409
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 409

    # ronda 2 = 2 ganadores + 2 byes = 4 equipos -> 2 partidos
    _finalizar_ronda(db_session, tid, 1)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 200, r.text
    assert r.json() == {"ronda": 2, "partidos_creados": 2, "estado": "en_curso"}

    # ronda 3: la final
    _finalizar_ronda(db_session, tid, 2)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-19", "hora_base": "10:00"})
    assert r.status_code == 200 and r.json()["partidos_creados"] == 1

    # campeón: el torneo finaliza
    _finalizar_ronda(db_session, tid, 3)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-26", "hora_base": "10:00"})
    assert r.status_code == 200
    assert r.json()["estado"] == "finalizado" and r.json()["partidos_creados"] == 0
    assert "campeon" in r.json()
    torneo = client.get(f"/torneos/{tid}", headers=auth_admin).json()
    assert torneo["estado"] == "finalizado"


def test_siguiente_ronda_rechaza_liga(client, db_session, auth_admin):
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "16:00"})
    assert r.status_code == 400
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py -v`
Expected: los 2 nuevos FAIL (404/405); el resto PASS.

- [ ] **Step 3: Implementar**

En `api/app/routers/torneos.py`, debajo de `iniciar_torneo`:

```python
@router.post("/{torneo_id}/siguiente-ronda")
def siguiente_ronda(
    torneo_id: int,
    datos: TorneoSiguienteRonda,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    if calendario.normalizar_tipo(torneo.tipo) != "eliminacion directa":
        raise HTTPException(status_code=400,
                            detail="Solo aplica a torneos de eliminación directa")
    if torneo.estado != "en_curso":
        raise HTTPException(status_code=409, detail="El torneo no está en curso")

    partidos = db.query(models.Partido).filter_by(torneo_id=torneo.id).all()
    ronda_actual = max((p.jornada or 0) for p in partidos)
    de_ronda = [p for p in partidos if (p.jornada or 0) == ronda_actual]
    pendientes = [p for p in de_ronda if p.estado != "finalizado"]
    if pendientes:
        raise HTTPException(
            status_code=409,
            detail=f"Faltan {len(pendientes)} partidos de la ronda {ronda_actual} por finalizar")

    # El empate es imposible en eliminación (lo bloquea /finalizar).
    ganadores = [p.equipo_local_id if p.goles_local > p.goles_visitante
                 else p.equipo_visitante_id for p in de_ronda]
    if ronda_actual == 1:
        # Byes derivados: aceptados que no jugaron la ronda 1.
        jugaron = ({p.equipo_local_id for p in de_ronda}
                   | {p.equipo_visitante_id for p in de_ronda})
        aceptados = [i.equipo_id for i in
                     db.query(models.Inscripcion)
                     .filter_by(torneo_id=torneo.id, estado="aceptada").all()]
        ganadores += [e for e in aceptados if e not in jugaron]

    if len(ganadores) == 1:
        torneo.estado = "finalizado"
        db.commit()
        campeon = db.get(models.Equipo, ganadores[0])
        return {"campeon_id": campeon.id, "campeon": campeon.nombre,
                "estado": "finalizado", "partidos_creados": 0}

    # ganadores + byes suman potencia de 2 -> aquí ya no hay byes nuevos.
    _byes, parejas = calendario.generar_ronda_eliminacion(ganadores, random.Random())
    base = datetime.combine(datos.fecha, datos.hora_base, tzinfo=timezone.utc)
    creados = _crear_partidos(db, torneo, [parejas], base,
                              _canchas_de_la_sede(db, torneo),
                              primera_jornada=ronda_actual + 1)
    db.commit()
    return {"ronda": ronda_actual + 1, "partidos_creados": creados,
            "estado": torneo.estado}
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd api && .venv/bin/pytest tests/test_torneo_iniciar.py -v`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/torneos.py api/tests/test_torneo_iniciar.py
git commit -m "feat(api): siguiente ronda de eliminacion (ganadores + byes, campeon)"
```

---

### Task 5: Reglas de árbitro y de empate en partidos

**Files:**
- Modify: `api/app/routers/partidos.py` (imports; `crear_partido` ~L98; `actualizar_partido` ~L136; `finalizar_partido` ~L251; helper y endpoint nuevos)
- Test: `api/tests/test_arbitro_reglas.py` (nuevo)

**Interfaces:**
- Consumes: `calendario.normalizar_tipo` (Task 2).
- Produces: `GET /partidos/{id}/arbitros-disponibles` → `[{"id", "nombre"}]` (lo consume el panel en la Task 6). 409 por choque en crear/actualizar; 409 por empate en finalizar (eliminación).

- [ ] **Step 1: Tests que fallan**

Crear `api/tests/test_arbitro_reglas.py`:

```python
"""Choque de horario del árbitro, disponibilidad y empate en eliminación."""


def _torneo(client, auth_admin, tipo="Liga"):
    return client.post("/torneos", headers=auth_admin,
                       json={"nombre": f"T {tipo}", "sede_id": 1, "tipo": tipo}).json()["id"]


def _partido(client, auth_admin, tid, **over):
    body = {"torneo_id": tid, "equipo_local_id": 1, "equipo_visitante_id": 2}
    body.update(over)
    return client.post("/partidos", headers=auth_admin, json=body)


def test_choque_de_horario_al_crear(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    r1 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    assert r1.status_code == 201, r1.text
    # mismo árbitro, misma fecha/hora -> 409
    r2 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    assert r2.status_code == 409
    # misma fecha, otra hora -> OK
    r3 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T18:00:00Z")
    assert r3.status_code == 201, r3.text


def test_choque_de_horario_al_actualizar(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    _partido(client, auth_admin, tid,
             arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    libre = _partido(client, auth_admin, tid,
                     fecha_hora="2026-09-05T16:00:00Z").json()["id"]
    r = client.put(f"/partidos/{libre}", headers=auth_admin,
                   json={"arbitro_id": arbitro_id})
    assert r.status_code == 409
    # reasignarle al MISMO partido su propio árbitro no choca consigo mismo
    ocupado = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()[0]["id"]
    r = client.put(f"/partidos/{ocupado}", headers=auth_admin,
                   json={"arbitro_id": arbitro_id})
    assert r.status_code == 200, r.text


def test_arbitros_disponibles_filtra_ocupados(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    _partido(client, auth_admin, tid,
             arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    otro = _partido(client, auth_admin, tid,
                    fecha_hora="2026-09-05T16:00:00Z").json()["id"]
    disponibles = client.get(f"/partidos/{otro}/arbitros-disponibles",
                             headers=auth_admin).json()
    assert arbitro_id not in [a["id"] for a in disponibles]
    # sin fecha_hora no hay choque posible: aparece
    sin_fecha = _partido(client, auth_admin, tid).json()["id"]
    disponibles = client.get(f"/partidos/{sin_fecha}/arbitros-disponibles",
                             headers=auth_admin).json()
    assert arbitro_id in [a["id"] for a in disponibles]


def _en_juego_empatado(db_session, tid, arbitro_id, goles=(1, 1)):
    from app import models
    db = db_session()
    p = models.Partido(torneo_id=tid, equipo_local_id=1, equipo_visitante_id=2,
                       arbitro_id=arbitro_id, estado="en_juego",
                       goles_local=goles[0], goles_visitante=goles[1])
    db.add(p)
    db.commit()
    pid = p.id
    db.close()
    return pid


def test_eliminacion_no_finaliza_empatado(client, db_session, auth_admin,
                                          auth_arbitro, arbitro_id):
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    pid = _en_juego_empatado(db_session, tid, arbitro_id)
    r = client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    assert r.status_code == 409
    # con desempate sí finaliza
    pid2 = _en_juego_empatado(db_session, tid, arbitro_id, goles=(2, 1))
    r = client.post(f"/partidos/{pid2}/finalizar", headers=auth_arbitro)
    assert r.status_code == 200, r.text


def test_liga_si_puede_finalizar_empatada(client, db_session, auth_admin,
                                          auth_arbitro, arbitro_id):
    tid = _torneo(client, auth_admin, tipo="Liga")
    pid = _en_juego_empatado(db_session, tid, arbitro_id)
    r = client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    assert r.status_code == 200, r.text
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_reglas.py -v`
Expected: FALLAN los de choque (hoy devuelve 201/200), el de disponibles (404) y el de empate (hoy 200). `test_liga_si_puede_finalizar_empatada` puede PASAR ya (documenta el contrato).

- [ ] **Step 3: Implementar**

En `api/app/routers/partidos.py`:

1. Import: agregar `from app import calendario` junto a los imports de `app`.
2. Helper (junto a `_avisar_partido`):

```python
def _arbitro_ocupado(db, arbitro_id, fecha_hora, excluir_id=None) -> bool:
    """True si el árbitro ya tiene OTRO partido no finalizado a esa hora exacta."""
    if not arbitro_id or not fecha_hora:
        return False
    q = db.query(models.Partido).filter(
        models.Partido.arbitro_id == arbitro_id,
        models.Partido.fecha_hora == fecha_hora,
        models.Partido.estado != "finalizado",
    )
    if excluir_id is not None:
        q = q.filter(models.Partido.id != excluir_id)
    return db.query(q.exists()).scalar()
```

3. En `crear_partido`, después de la validación del árbitro (tras el `raise` de "El árbitro indicado no es válido"):

```python
        if _arbitro_ocupado(db, datos.arbitro_id, datos.fecha_hora):
            raise HTTPException(status_code=409,
                                detail="El árbitro ya tiene un partido a esa hora")
```

4. En `actualizar_partido`, después de la validación de la cancha y ANTES del bucle de `setattr`:

```python
    arbitro_final = cambios.get("arbitro_id", partido.arbitro_id)
    fecha_final = cambios.get("fecha_hora", partido.fecha_hora)
    if ("arbitro_id" in cambios or "fecha_hora" in cambios) and _arbitro_ocupado(
            db, arbitro_final, fecha_final, excluir_id=partido.id):
        raise HTTPException(status_code=409,
                            detail="El árbitro ya tiene un partido a esa hora")
```

5. En `finalizar_partido`, después del 409 de "Solo se puede finalizar un partido en juego":

```python
    if (calendario.normalizar_tipo(partido.torneo.tipo) == "eliminacion directa"
            and partido.goles_local == partido.goles_visitante):
        raise HTTPException(
            status_code=409,
            detail="En eliminación directa el partido no puede terminar empatado")
```

6. Endpoint nuevo, junto a los GET de lectura:

```python
@router.get("/{partido_id}/arbitros-disponibles")
def arbitros_disponibles(
    partido_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    """Árbitros activos sin choque con la fecha/hora de este partido.
    El propio árbitro asignado siempre aparece (para mostrarlo elegido)."""
    partido = _obtener_partido(db, partido_id)
    arbitros = (db.query(models.Usuario)
                .join(models.Rol, models.Usuario.rol_id == models.Rol.id)
                .filter(models.Rol.nombre == "arbitro",
                        models.Usuario.activo.is_(True))
                .order_by(models.Usuario.nombre).all())
    return [{"id": a.id, "nombre": a.nombre} for a in arbitros
            if a.id == partido.arbitro_id
            or not _arbitro_ocupado(db, a.id, partido.fecha_hora,
                                    excluir_id=partido.id)]
```

- [ ] **Step 4: Verificar que pasan (más regresión de partidos)**

Run: `cd api && .venv/bin/pytest tests/test_arbitro_reglas.py tests/test_partidos.py tests/test_torneo_iniciar.py -v`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/partidos.py api/tests/test_arbitro_reglas.py
git commit -m "feat(api): choque de horario del arbitro, disponibles y empate en eliminacion"
```

---

### Task 6: Panel web (botones, formularios y asignación de árbitro)

**Files:**
- Modify: `web/app/app.py` (ruta `torneos()` ~L203; ruta `partido_detalle()` ~L534; 3 rutas nuevas)
- Modify: `web/app/templates/torneos.html` (celda de acciones)
- Modify: `web/app/templates/torneo_nuevo.html` (campo tipo, líneas 38-39)
- Modify: `web/app/templates/partido_detalle.html` (antes de `<!-- Alineaciones -->`)
- Create: `web/app/templates/torneo_iniciar.html`

**Interfaces:**
- Consumes: `POST /torneos/{id}/iniciar` y `/siguiente-ronda` (Tasks 3-4), `GET /partidos/{id}/arbitros-disponibles` y `PUT /partidos/{id}` (Task 5).
- Produces: nada aguas abajo. Sin tests automatizados de web (no existen en el repo): verificación de sintaxis + validación visual del usuario tras el despliegue.

- [ ] **Step 1: Rutas en `web/app/app.py`**

Helper (junto a `_detalle_error`):

```python
def _tipo_normalizado(tipo):
    """Espejo de calendario.normalizar_tipo (el panel no importa el paquete api)."""
    import unicodedata
    if not tipo:
        return ""
    plano = "".join(c for c in unicodedata.normalize("NFD", tipo)
                    if unicodedata.category(c) != "Mn")
    return " ".join(plano.lower().split())
```

Reemplazar el cuerpo de `torneos()` para anotar el flag:

```python
@app.route("/torneos")
@login_required
def torneos():
    r = api_get("/torneos")
    if r.status_code == 401:
        return _sesion_expirada()
    lista = r.json() if r.status_code == 200 else []
    for t in lista:
        t["es_eliminacion"] = _tipo_normalizado(t.get("tipo")) == "eliminacion directa"
    return render_template("torneos.html", torneos=lista)
```

Rutas nuevas (después de `torneo_nuevo`):

```python
@app.route("/torneos/<int:torneo_id>/iniciar", methods=["GET", "POST"])
@login_required
def torneo_iniciar(torneo_id):
    if request.method == "POST":
        r = api_post(f"/torneos/{torneo_id}/iniciar", {
            "primera_fecha": request.form.get("fecha", "").strip(),
            "hora_base": request.form.get("hora", "").strip(),
        })
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 200:
            flash(f"Torneo iniciado: {r.json().get('partidos_creados', 0)} partidos creados.", "ok")
        else:
            flash(_detalle_error(r, "No se pudo iniciar el torneo."), "error")
        return redirect(url_for("torneos"))
    rt = api_get(f"/torneos/{torneo_id}")
    if rt.status_code == 401:
        return _sesion_expirada()
    if rt.status_code != 200:
        flash("Torneo no encontrado.", "error")
        return redirect(url_for("torneos"))
    return render_template("torneo_iniciar.html", torneo=rt.json(), modo="iniciar")


@app.route("/torneos/<int:torneo_id>/siguiente-ronda", methods=["GET", "POST"])
@login_required
def torneo_siguiente_ronda(torneo_id):
    if request.method == "POST":
        r = api_post(f"/torneos/{torneo_id}/siguiente-ronda", {
            "fecha": request.form.get("fecha", "").strip(),
            "hora_base": request.form.get("hora", "").strip(),
        })
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 200:
            cuerpo = r.json()
            if cuerpo.get("estado") == "finalizado":
                flash(f"¡Campeón: {cuerpo.get('campeon', '?')}! Torneo finalizado.", "ok")
            else:
                flash(f"Ronda {cuerpo.get('ronda')}: {cuerpo.get('partidos_creados')} partidos creados.", "ok")
        else:
            flash(_detalle_error(r, "No se pudo generar la siguiente ronda."), "error")
        return redirect(url_for("torneos"))
    rt = api_get(f"/torneos/{torneo_id}")
    if rt.status_code == 401:
        return _sesion_expirada()
    if rt.status_code != 200:
        flash("Torneo no encontrado.", "error")
        return redirect(url_for("torneos"))
    return render_template("torneo_iniciar.html", torneo=rt.json(), modo="siguiente-ronda")


@app.route("/partidos/<int:partido_id>/arbitro", methods=["POST"])
@login_required
def partido_asignar_arbitro(partido_id):
    r = api_put(f"/partidos/{partido_id}", {"arbitro_id": int(request.form.get("arbitro_id", 0))})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash("Árbitro asignado.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo asignar el árbitro."), "error")
    return redirect(url_for("partido_detalle", partido_id=partido_id))
```

En `partido_detalle()` (~L534), antes del `render_template`, agregar:

```python
    disponibles = []
    if partido.get("estado") == "programado":
        ra = api_get(f"/partidos/{partido_id}/arbitros-disponibles")
        disponibles = ra.json() if ra.status_code == 200 else []
```

y pasar `disponibles=disponibles` al `render_template` existente.

- [ ] **Step 2: Plantillas**

`web/app/templates/torneos.html` — en la celda de acciones (la del botón "Tabla"), agregar antes del enlace de Tabla:

```jinja
          {% if t.estado == 'programado' %}
          <a href="{{ url_for('torneo_iniciar', torneo_id=t.id) }}" class="btn" style="padding:7px 14px;">Iniciar torneo</a>
          {% elif t.estado == 'en_curso' and t.es_eliminacion %}
          <a href="{{ url_for('torneo_siguiente_ronda', torneo_id=t.id) }}" class="btn" style="padding:7px 14px;">Siguiente ronda</a>
          {% endif %}
```

`web/app/templates/torneo_nuevo.html` — reemplazar el `<input type="text" id="tipo" ...>` (línea 39) por:

```html
      <select id="tipo" name="tipo">
        <option value="liga">Liga</option>
        <option value="eliminacion directa">Eliminación directa</option>
      </select>
```

Crear `web/app/templates/torneo_iniciar.html`:

```jinja
{% extends "base.html" %}
{% set active = 'torneos' %}
{% block title %}{{ 'Iniciar torneo' if modo == 'iniciar' else 'Siguiente ronda' }}{% endblock %}
{% block heading %}{{ 'Iniciar torneo' if modo == 'iniciar' else 'Siguiente ronda' }}{% endblock %}

{% block content %}
<div class="card form-card">
  <h2 style="margin-bottom:6px;">{{ torneo.nombre }}</h2>
  <p class="sub" style="margin-bottom:18px;">
    {% if modo == 'iniciar' %}
    Se generará el calendario completo ({{ torneo.tipo or 'tipo sin definir' }}) y el torneo pasará a “en curso”.
    {% else %}
    Se crearán los cruces de la siguiente ronda con los ganadores.
    {% endif %}
  </p>
  <form method="post">
    <div class="field">
      <label for="fecha">{{ 'Fecha de la primera jornada' if modo == 'iniciar' else 'Fecha de la ronda' }}</label>
      <input type="date" id="fecha" name="fecha" required>
    </div>
    <div class="field">
      <label for="hora">Hora del primer partido (los demás van cada 2 horas)</label>
      <input type="time" id="hora" name="hora" value="16:00" required>
    </div>
    <button class="btn" type="submit">{{ 'Iniciar torneo' if modo == 'iniciar' else 'Generar ronda' }}</button>
    <a class="btn ghost" href="{{ url_for('torneos') }}">Cancelar</a>
  </form>
</div>
{% endblock %}
```

`web/app/templates/partido_detalle.html` — insertar ANTES de la línea `<!-- Alineaciones -->`:

```jinja
<!-- Árbitro -->
<div class="card" style="margin-bottom:18px;">
  <div class="label">Árbitro</div>
  <p style="margin:10px 0;">{{ partido.arbitro_nombre or 'Sin asignar' }}</p>
  {% if disponibles %}
  <form method="post" action="{{ url_for('partido_asignar_arbitro', partido_id=partido.id) }}" style="display:flex; gap:10px; align-items:center;">
    <select name="arbitro_id" required>
      {% for a in disponibles %}
      <option value="{{ a.id }}" {{ 'selected' if a.id == partido.arbitro_id else '' }}>{{ a.nombre }}</option>
      {% endfor %}
    </select>
    <button class="btn" type="submit">Asignar árbitro</button>
  </form>
  {% elif partido.estado == 'programado' %}
  <p class="sub">No hay árbitros disponibles para esta fecha y hora.</p>
  {% endif %}
</div>
```

- [ ] **Step 3: Verificación de sintaxis (no hay suite web)**

Run: `python3 -c "import ast; ast.parse(open('web/app/app.py').read()); print('app.py OK')"`
Expected: `app.py OK`. Las plantillas se validan visualmente tras el despliegue (sin navegador headless — regla del proyecto).

- [ ] **Step 4: Commit**

```bash
git add web/app/app.py web/app/templates/torneos.html web/app/templates/torneo_nuevo.html web/app/templates/torneo_iniciar.html web/app/templates/partido_detalle.html
git commit -m "feat(web): iniciar torneo, siguiente ronda y asignacion de arbitro en el panel"
```

---

### Task 7: Suite completa, push y PR

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa de la API**

Run: `cd api && .venv/bin/pytest -q`
Expected: **todos en verde** (284 previos + 22 nuevos = 306). Tarda ~7 min.

- [ ] **Step 2: Push y PR**

⚠️ Regla del proyecto: pedir aprobación del usuario antes del push/PR si no la dio ya.

```bash
git push -u origin feat/iniciar-torneo
gh pr create --title "Iniciar torneo: calendario automático y asignación de árbitros" --body "..."
```

El cuerpo del PR debe resumir: migración `jornada`, generadores puros (liga ida/vuelta, eliminación con byes a potencia de 2 — regla aportada por el usuario), los 3 endpoints, las 2 reglas nuevas (choque de árbitro, empate en eliminación), el panel, y el recordatorio de despliegue: **correr la migración con el contenedor efímero antes del `up -d --build api1 api2 web`**.
