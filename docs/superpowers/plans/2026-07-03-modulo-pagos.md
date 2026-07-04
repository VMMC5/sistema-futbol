# Módulo de Pagos (IF-10) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el pago en línea (pasarela simulada) de reservas de cancha y de cuotas de inscripción de equipos a torneos, con tarjeta y transferencia, comprobante en app y PDF.

**Architecture:** Router delgado (HTTP + auth) → `pagos_service` (orquesta cálculo de monto, cobro, confirmación, notificación) → `PaymentGateway`/`MockGateway` (costura para Stripe futuro). El monto SIEMPRE se calcula en el servidor.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, pytest + TestClient (SQLite en memoria), fpdf2 (PDF), Expo/React Native (móvil), Flask (panel admin).

## Global Constraints

- Python: FastAPI 0.115.6, SQLAlchemy 2.0.36, Pydantic v2. Copiar el estilo de los routers existentes (`api/app/routers/*.py`).
- El cliente NUNCA envía el monto; se calcula en el servidor.
- No se persisten PAN/CVV: solo los últimos 4 dígitos dentro de `referencia`.
- Estados de `Pago`: `pendiente` → `completado` | `fallido`. Método: `tarjeta` | `transferencia`.
- Tests: SQLite en memoria vía `conftest.py`; autenticación con las fixtures existentes (`auth_admin`, `auth_entrenador`, etc.) y el helper de registrar jugador.
- Todos los comandos de test se ejecutan desde `api/`: `cd api && python -m pytest ...`.
- Trabajo en la rama `feature/modulo-pagos` (ya creada).

---

### Task 1: Modelo `Pago` + migración + dependencia PDF

**Files:**
- Modify: `api/app/models.py` (clase `Pago`, ~línea 339)
- Modify: `api/requirements.txt`
- Create: `api/migrations/versions/20260703_1000_pagos_concepto_completado.py`
- Test: `api/tests/test_pagos_modelo.py`

**Interfaces:**
- Produces: `Pago.concepto: str|None`, `Pago.completado_en: datetime|None`, property `Pago.usuario_nombre -> str|None`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_modelo.py`:

```python
"""El modelo Pago admite concepto, completado_en y expone usuario_nombre."""
from datetime import datetime, timezone

from app import models


def test_pago_admite_concepto_y_completado(db_session):
    db = db_session()
    pago = models.Pago(
        usuario_id=1, monto=200, metodo="tarjeta", estado="completado",
        referencia="MOCK-ABCD1234", concepto="Reserva Cancha 1",
        completado_en=datetime.now(timezone.utc),
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    assert pago.concepto == "Reserva Cancha 1"
    assert pago.completado_en is not None
    assert pago.usuario_nombre == "Admin"   # usuario id=1 es 'Admin' en conftest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_modelo.py -v`
Expected: FAIL (`TypeError: 'concepto' is an invalid keyword argument` o `AttributeError: usuario_nombre`).

- [ ] **Step 3: Add columns and property to `Pago`**

En `api/app/models.py`, dentro de `class Pago(Base)`, después de `referencia = Column(...)` y antes de `creado_en`:

```python
    concepto = Column(String(160))                # snapshot legible para recibo/historial
    completado_en = Column(DateTime(timezone=True))
```

Y al final de la clase `Pago`, después de las `relationship`, añade:

```python
    @property
    def usuario_nombre(self):
        return self.usuario.nombre if self.usuario else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_pagos_modelo.py -v`
Expected: PASS.

- [ ] **Step 5: Add fpdf2 dependency**

En `api/requirements.txt`, después de `python-multipart==0.0.20`, añade:

```
fpdf2==2.8.1                    # generacion del PDF del comprobante de pago
```

- [ ] **Step 6: Create Alembic migration**

Crea `api/migrations/versions/20260703_1000_pagos_concepto_completado.py`:

```python
"""pagos: concepto y completado_en

Revision ID: 20260703_1000
Revises: 20260613_2057
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260703_1000"
down_revision = "20260613_2057"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pagos", sa.Column("concepto", sa.String(length=160), nullable=True))
    op.add_column("pagos", sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("pagos", "completado_en")
    op.drop_column("pagos", "concepto")
```

Nota: confirma que `down_revision` coincide con el `revision` del archivo `api/migrations/versions/20260613_2057_panel_del_jugador.py` (ábrelo y copia su `revision` exacto si difiere).

- [ ] **Step 7: Commit**

```bash
git add api/app/models.py api/requirements.txt api/migrations/versions/20260703_1000_pagos_concepto_completado.py api/tests/test_pagos_modelo.py
git commit -m "feat(pagos): columnas concepto/completado_en y migracion"
```

---

### Task 2: `MockGateway` (pasarela simulada)

**Files:**
- Create: `api/app/gateway.py`
- Test: `api/tests/test_gateway.py`

**Interfaces:**
- Produces:
  - `ResultadoCobro` (dataclass): `estado: str` (`"completado"|"fallido"|"pendiente"`), `referencia: str`, `motivo: str|None`.
  - `class PaymentGateway` con `charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro`.
  - `class MockGateway(PaymentGateway)`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_gateway.py`:

```python
"""Reglas del MockGateway: tarjeta aprueba/rechaza y transferencia queda pendiente."""
from decimal import Decimal

from app.gateway import MockGateway


def test_tarjeta_aprobada():
    g = MockGateway()
    r = g.charge(Decimal("200.00"), "tarjeta", {"numero": "4111111111111234", "titular": "Ana"})
    assert r.estado == "completado"
    assert r.referencia.startswith("MOCK-")
    assert r.referencia.endswith("1234")   # ultimos 4 digitos


def test_tarjeta_rechazada_termina_en_0000():
    g = MockGateway()
    r = g.charge(Decimal("200.00"), "tarjeta", {"numero": "4111111111110000", "titular": "Ana"})
    assert r.estado == "fallido"
    assert r.motivo is not None


def test_transferencia_queda_pendiente():
    g = MockGateway()
    r = g.charge(Decimal("500.00"), "transferencia", None)
    assert r.estado == "pendiente"
    assert r.referencia.startswith("TRF-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_gateway.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.gateway'`).

- [ ] **Step 3: Implement the gateway**

Create `api/app/gateway.py`:

```python
"""
Pasarela de pago simulada (mock).

No cobra dinero real: decide de forma DETERMINISTA para poder demostrar y
probar los dos caminos. Sustituir MockGateway por un StripeGateway que
implemente la misma interfaz es todo lo que hará falta para pagos reales.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4


@dataclass
class ResultadoCobro:
    estado: str            # "completado" | "fallido" | "pendiente"
    referencia: str
    motivo: str | None = None


class PaymentGateway:
    def charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro:
        raise NotImplementedError


class MockGateway(PaymentGateway):
    """- tarjeta: aprueba, salvo que el número termine en 0000 (fondos insuficientes).
       - transferencia: queda pendiente hasta que el superadmin la confirme."""

    def charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro:
        folio = uuid4().hex[:8].upper()
        if metodo == "transferencia":
            return ResultadoCobro(estado="pendiente", referencia=f"TRF-{folio}")

        # tarjeta
        numero = (datos_tarjeta or {}).get("numero", "")
        ultimos4 = numero[-4:]
        if ultimos4 == "0000":
            return ResultadoCobro(estado="fallido", referencia=f"MOCK-{folio}",
                                  motivo="Tarjeta rechazada (fondos insuficientes)")
        return ResultadoCobro(estado="completado", referencia=f"MOCK-{folio}·{ultimos4}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_gateway.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add api/app/gateway.py api/tests/test_gateway.py
git commit -m "feat(pagos): MockGateway con reglas deterministas"
```

---

### Task 3: Esquemas Pydantic de pagos e inscripciones

**Files:**
- Modify: `api/app/schemas.py` (añadir al final)
- Test: `api/tests/test_pagos_schemas.py`

**Interfaces:**
- Produces:
  - `DatosTarjeta`: `numero: str`, `exp_mes: int`, `exp_anio: int`, `cvv: str`, `titular: str`.
  - `PagoCreate`: `metodo: Literal["tarjeta","transferencia"]`, `tarjeta: DatosTarjeta | None`.
  - `PagoOut`: `id, concepto, monto, metodo, estado, referencia, creado_en, completado_en, usuario_nombre`.
  - `InscripcionCreate`: `torneo_id: int`, `equipo_id: int`.
  - `InscripcionOut`: `id, torneo_id, torneo_nombre, equipo_id, equipo_nombre, estado, pago_id`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_schemas.py`:

```python
"""Validación de datos de tarjeta en PagoCreate."""
import pytest
from pydantic import ValidationError

from app.schemas import PagoCreate


def _tarjeta(**over):
    base = {"numero": "4111111111111111", "exp_mes": 12, "exp_anio": 2999,
            "cvv": "123", "titular": "Ana Perez"}
    base.update(over)
    return base


def test_tarjeta_valida():
    p = PagoCreate(metodo="tarjeta", tarjeta=_tarjeta())
    assert p.tarjeta.numero == "4111111111111111"


def test_tarjeta_requerida_si_metodo_tarjeta():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=None)


def test_numero_no_numerico_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(numero="41111abc1111"))


def test_cvv_de_2_digitos_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(cvv="12"))


def test_expiracion_pasada_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(exp_mes=1, exp_anio=2000))


def test_transferencia_no_requiere_tarjeta():
    p = PagoCreate(metodo="transferencia")
    assert p.tarjeta is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_schemas.py -v`
Expected: FAIL (`ImportError: cannot import name 'PagoCreate'`).

- [ ] **Step 3: Add schemas**

Al final de `api/app/schemas.py` añade (los imports `datetime`, `EmailStr`, `Field`, `model_validator` ya están en el archivo):

```python
# ======================================================================
#  PAGOS
# ======================================================================
from typing import Literal
from pydantic import field_validator


class DatosTarjeta(BaseModel):
    numero: str
    exp_mes: int = Field(ge=1, le=12)
    exp_anio: int
    cvv: str
    titular: str = Field(min_length=2, max_length=80)

    @field_validator("numero")
    @classmethod
    def _numero_valido(cls, v: str) -> str:
        limpio = v.replace(" ", "")
        if not limpio.isdigit() or not (13 <= len(limpio) <= 19):
            raise ValueError("número de tarjeta inválido")
        return limpio

    @field_validator("cvv")
    @classmethod
    def _cvv_valido(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 3:
            raise ValueError("CVV inválido")
        return v


class PagoCreate(BaseModel):
    metodo: Literal["tarjeta", "transferencia"]
    tarjeta: DatosTarjeta | None = None

    @model_validator(mode="after")
    def _coherencia(self):
        if self.metodo == "tarjeta":
            if self.tarjeta is None:
                raise ValueError("faltan los datos de la tarjeta")
            hoy = datetime.now()
            if (self.tarjeta.exp_anio, self.tarjeta.exp_mes) < (hoy.year, hoy.month):
                raise ValueError("la tarjeta está vencida")
        return self


class PagoOut(BaseModel):
    id: int
    concepto: str | None = None
    monto: float
    metodo: str
    estado: str
    referencia: str | None = None
    creado_en: datetime | None = None
    completado_en: datetime | None = None
    usuario_nombre: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  INSCRIPCIONES (equipo a torneo)
# ======================================================================
class InscripcionCreate(BaseModel):
    torneo_id: int
    equipo_id: int


class InscripcionOut(BaseModel):
    id: int
    torneo_id: int
    torneo_nombre: str | None = None
    equipo_id: int
    equipo_nombre: str | None = None
    estado: str
    pago_id: int | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_pagos_schemas.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Add convenience properties for InscripcionOut**

En `api/app/models.py`, dentro de `class Inscripcion(Base)`, añade después de las `relationship`:

```python
    @property
    def torneo_nombre(self):
        return self.torneo.nombre if self.torneo else None

    @property
    def equipo_nombre(self):
        return self.equipo.nombre if self.equipo else None
```

- [ ] **Step 6: Commit**

```bash
git add api/app/schemas.py api/app/models.py api/tests/test_pagos_schemas.py
git commit -m "feat(pagos): schemas de pago e inscripcion + propiedades de nombre"
```

---

### Task 4: `pagos_service` — cálculo de monto

**Files:**
- Create: `api/app/pagos_service.py`
- Test: `api/tests/test_pagos_service.py`

**Interfaces:**
- Produces:
  - `calcular_monto_reserva(cancha, hora_inicio, hora_fin) -> Decimal`
  - `calcular_monto_inscripcion(torneo) -> Decimal`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_service.py`:

```python
"""Cálculo de monto en el servidor (nunca lo envía el cliente)."""
from datetime import time
from decimal import Decimal
from types import SimpleNamespace

from app import pagos_service


def test_monto_reserva_una_hora():
    cancha = SimpleNamespace(precio_hora=Decimal("200.00"), nombre="Cancha 1")
    monto = pagos_service.calcular_monto_reserva(cancha, time(10, 0), time(11, 0))
    assert monto == Decimal("200.00")


def test_monto_reserva_hora_y_media():
    cancha = SimpleNamespace(precio_hora=Decimal("200.00"), nombre="Cancha 1")
    monto = pagos_service.calcular_monto_reserva(cancha, time(10, 0), time(11, 30))
    assert monto == Decimal("300.00")


def test_monto_inscripcion():
    torneo = SimpleNamespace(cuota_inscripcion=Decimal("500.00"))
    assert pagos_service.calcular_monto_inscripcion(torneo) == Decimal("500.00")


def test_monto_inscripcion_gratis():
    torneo = SimpleNamespace(cuota_inscripcion=None)
    assert pagos_service.calcular_monto_inscripcion(torneo) == Decimal("0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_service.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.pagos_service'`).

- [ ] **Step 3: Implement the calculation functions**

Create `api/app/pagos_service.py`:

```python
"""
Lógica de pagos (orquestación). El router solo hace HTTP + autorización;
aquí vive el cálculo de monto, el cobro contra el gateway, la confirmación
de reserva/inscripción y la notificación.

El monto se calcula SIEMPRE en el servidor a partir de la cancha/torneo,
nunca se toma del cliente.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.gateway import MockGateway, PaymentGateway
from app.schemas import PagoCreate

_gateway: PaymentGateway = MockGateway()

_DOS_DEC = Decimal("0.01")


def calcular_monto_reserva(cancha, hora_inicio, hora_fin) -> Decimal:
    if cancha.precio_hora is None:
        raise HTTPException(status_code=400, detail="La cancha no tiene precio configurado")
    inicio = datetime.combine(date.min, hora_inicio)
    fin = datetime.combine(date.min, hora_fin)
    horas = Decimal((fin - inicio).total_seconds()) / Decimal(3600)
    return (Decimal(cancha.precio_hora) * horas).quantize(_DOS_DEC, ROUND_HALF_UP)


def calcular_monto_inscripcion(torneo) -> Decimal:
    cuota = torneo.cuota_inscripcion
    if cuota is None or Decimal(cuota) <= 0:
        return Decimal("0")
    return Decimal(cuota).quantize(_DOS_DEC, ROUND_HALF_UP)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_pagos_service.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add api/app/pagos_service.py api/tests/test_pagos_service.py
git commit -m "feat(pagos): calculo de monto en el servidor"
```

---

### Task 5: Pago de reserva con tarjeta (router + servicio + registro)

**Files:**
- Modify: `api/app/pagos_service.py` (añadir orquestación)
- Create: `api/app/routers/pagos.py`
- Modify: `api/app/main.py` (registrar router)
- Modify: `api/tests/conftest.py` (dar precio a la cancha sembrada)
- Test: `api/tests/test_pagos.py`

**Interfaces:**
- Consumes: `calcular_monto_reserva`, `MockGateway`, `PagoCreate`, `PagoOut`.
- Produces:
  - `pagos_service.pagar_reserva(db, usuario, reserva, datos: PagoCreate, gateway=None) -> models.Pago`
  - Router `POST /pagos/reserva/{reserva_id}` → `PagoOut`.

- [ ] **Step 1: Give the seeded cancha a price (fixture)**

En `api/tests/conftest.py`, cambia la línea que crea la cancha (≈línea 48):

```python
    db.add(models.Cancha(sede_id=1, nombre="Cancha 1", tipo="futbol 7", disponible=True))
```

por:

```python
    db.add(models.Cancha(sede_id=1, nombre="Cancha 1", tipo="futbol 7",
                         precio_hora=200, disponible=True))
```

- [ ] **Step 2: Write the failing test**

Create `api/tests/test_pagos.py`:

```python
"""Pago de reservas (tarjeta)."""

TARJETA_OK = {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
              "cvv": "123", "titular": "Ana Perez"}
TARJETA_RECHAZO = {**TARJETA_OK, "numero": "4111111111110000"}
RESERVA_BASE = {"cancha_id": 1, "fecha": "2026-08-01", "hora_inicio": "10:00", "hora_fin": "11:00"}


def _jugador(client, correo="ana@demo.com"):
    client.post("/auth/register", json={"nombre": "Ana", "correo": correo, "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": correo, "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _reserva(client, auth):
    return client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]


def test_pago_tarjeta_confirma_reserva(client):
    auth = _jugador(client)
    rid = _reserva(client, auth)
    r = client.post(f"/pagos/reserva/{rid}", headers=auth,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "completado"
    assert cuerpo["monto"] == 200.0            # 1 hora * 200 (calculado en el servidor)
    # la reserva quedó confirmada
    assert client.get(f"/reservas/{rid}", headers=auth).json()["estado"] == "confirmada"


def test_pago_tarjeta_rechazada_no_confirma(client):
    auth = _jugador(client)
    rid = _reserva(client, auth)
    r = client.post(f"/pagos/reserva/{rid}", headers=auth,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_RECHAZO})
    assert r.status_code == 402
    assert client.get(f"/reservas/{rid}", headers=auth).json()["estado"] == "pendiente"


def test_no_paga_reserva_ajena(client):
    ana = _jugador(client, "ana@demo.com")
    luis = _jugador(client, "luis@demo.com")
    rid = _reserva(client, ana)
    r = client.post(f"/pagos/reserva/{rid}", headers=luis,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 403


def test_no_se_paga_dos_veces(client):
    auth = _jugador(client)
    rid = _reserva(client, auth)
    client.post(f"/pagos/reserva/{rid}", headers=auth, json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    r = client.post(f"/pagos/reserva/{rid}", headers=auth, json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 409


def test_monto_lo_fija_el_servidor(client):
    """Aunque el cliente mande 'monto', se ignora (no es campo del schema)."""
    auth = _jugador(client)
    rid = _reserva(client, auth)
    r = client.post(f"/pagos/reserva/{rid}", headers=auth,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK, "monto": 1})
    assert r.json()["monto"] == 200.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos.py -v`
Expected: FAIL (404 en `/pagos/reserva/...` porque el router no existe).

- [ ] **Step 4: Add orchestration to `pagos_service.py`**

Añade al final de `api/app/pagos_service.py`:

```python
def _notificar(db: Session, usuario_id: int, titulo: str, mensaje: str) -> None:
    db.add(models.Notificacion(usuario_id=usuario_id, titulo=titulo, mensaje=mensaje))


def _procesar(db: Session, usuario: models.Usuario, monto: Decimal, concepto: str,
              datos: PagoCreate, gateway: PaymentGateway):
    datos_tarjeta = None
    if datos.metodo == "tarjeta":
        datos_tarjeta = {"numero": datos.tarjeta.numero, "titular": datos.tarjeta.titular}
    resultado = gateway.charge(monto, datos.metodo, datos_tarjeta)

    pago = models.Pago(
        usuario_id=usuario.id, monto=monto, metodo=datos.metodo,
        estado=resultado.estado, referencia=resultado.referencia, concepto=concepto,
    )
    if resultado.estado == "completado":
        pago.completado_en = datetime.now(timezone.utc)
    db.add(pago)
    db.flush()
    return pago, resultado


def pagar_reserva(db: Session, usuario: models.Usuario, reserva: models.Reserva,
                  datos: PagoCreate, gateway: PaymentGateway | None = None) -> models.Pago:
    gateway = gateway or _gateway

    if reserva.pago_id:
        previo = db.get(models.Pago, reserva.pago_id)
        if previo and previo.estado in ("completado", "pendiente"):
            raise HTTPException(status_code=409, detail="La reserva ya tiene un pago en curso o completado")

    monto = calcular_monto_reserva(reserva.cancha, reserva.hora_inicio, reserva.hora_fin)
    concepto = f"Reserva {reserva.cancha.nombre} · {reserva.fecha} {reserva.hora_inicio:%H:%M}"
    pago, resultado = _procesar(db, usuario, monto, concepto, datos, gateway)

    if resultado.estado == "completado":
        reserva.pago_id = pago.id
        reserva.estado = "confirmada"
        _notificar(db, usuario.id, "Pago confirmado",
                   f"Tu {concepto} quedó pagada. Folio {pago.referencia}.")
    elif resultado.estado == "pendiente":
        reserva.pago_id = pago.id
        _notificar(db, usuario.id, "Pago en revisión",
                   f"Registramos tu transferencia por {concepto}. Pendiente de confirmación.")

    db.commit()
    if resultado.estado == "fallido":
        raise HTTPException(status_code=402, detail=resultado.motivo or "Pago rechazado")
    db.refresh(pago)
    return pago
```

- [ ] **Step 5: Create the router**

Create `api/app/routers/pagos.py`:

```python
"""
Pagos en línea (pasarela simulada). Paga reservas e inscripciones a torneos.

Reglas de acceso:
- Pagar una reserva: su dueño.
- El monto lo calcula el servidor (nunca el cliente).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, pagos_service
from app.deps import get_current_user
from app.schemas import PagoCreate, PagoOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


@router.post("/reserva/{reserva_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_reserva(
    reserva_id: int,
    datos: PagoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = db.get(models.Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una reserva ajena")
    return pagos_service.pagar_reserva(db, usuario, reserva, datos)
```

- [ ] **Step 6: Register the router in `main.py`**

En `api/app/main.py`, añade `pagos` a la lista de imports de routers (línea ~13-17):

```python
from app.routers import (
    auth, torneos, reservas, partidos, estadisticas,
    sedes, canchas, usuarios, publico, solicitudes, equipos, invitaciones,
    notificaciones, jugador, pagos,
)
```

Y registra el router después de `estadisticas` (línea ~38):

```python
app.include_router(pagos.router, prefix="/pagos", tags=["pagos"])
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd api && python -m pytest tests/test_pagos.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Run the full suite (no regressions)**

Run: `cd api && python -m pytest -q`
Expected: todos en verde.

- [ ] **Step 9: Commit**

```bash
git add api/app/pagos_service.py api/app/routers/pagos.py api/app/main.py api/tests/conftest.py api/tests/test_pagos.py
git commit -m "feat(pagos): pago de reserva con tarjeta"
```

---

### Task 6: Transferencia + confirmación del admin

**Files:**
- Modify: `api/app/pagos_service.py` (añadir `confirmar_pago`)
- Modify: `api/app/routers/pagos.py` (añadir `POST /pagos/{id}/confirmar`)
- Test: `api/tests/test_pagos_transferencia.py`

**Interfaces:**
- Produces:
  - `pagos_service.confirmar_pago(db, pago) -> models.Pago`
  - Router `POST /pagos/{pago_id}/confirmar` (solo superadmin) → `PagoOut`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_transferencia.py`:

```python
"""Transferencia: queda pendiente y el superadmin la confirma."""

RESERVA_BASE = {"cancha_id": 1, "fecha": "2026-08-02", "hora_inicio": "10:00", "hora_fin": "11:00"}


def _jugador(client, correo="ana@demo.com"):
    client.post("/auth/register", json={"nombre": "Ana", "correo": correo, "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": correo, "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_transferencia_pendiente_luego_confirmada(client, auth_admin):
    auth = _jugador(client)
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]

    r = client.post(f"/pagos/reserva/{rid}", headers=auth, json={"metodo": "transferencia"})
    assert r.status_code == 201
    pago = r.json()
    assert pago["estado"] == "pendiente"
    # la reserva sigue pendiente hasta que el admin confirme
    assert client.get(f"/reservas/{rid}", headers=auth).json()["estado"] == "pendiente"

    # un no-admin no puede confirmar
    assert client.post(f"/pagos/{pago['id']}/confirmar", headers=auth).status_code == 403

    r2 = client.post(f"/pagos/{pago['id']}/confirmar", headers=auth_admin)
    assert r2.status_code == 200
    assert r2.json()["estado"] == "completado"
    assert client.get(f"/reservas/{rid}", headers=auth).json()["estado"] == "confirmada"


def test_no_se_confirma_un_pago_de_tarjeta(client, auth_admin):
    auth = _jugador(client)
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]
    pago = client.post(f"/pagos/reserva/{rid}", headers=auth,
                       json={"metodo": "tarjeta",
                             "tarjeta": {"numero": "4111111111111234", "exp_mes": 12,
                                         "exp_anio": 2999, "cvv": "123", "titular": "Ana"}}).json()
    r = client.post(f"/pagos/{pago['id']}/confirmar", headers=auth_admin)
    assert r.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_transferencia.py -v`
Expected: FAIL (404 en `/pagos/{id}/confirmar`).

- [ ] **Step 3: Add `confirmar_pago` to the service**

Añade al final de `api/app/pagos_service.py`:

```python
def confirmar_pago(db: Session, pago: models.Pago) -> models.Pago:
    """El superadmin confirma una transferencia pendiente."""
    if pago.metodo != "transferencia" or pago.estado != "pendiente":
        raise HTTPException(status_code=409,
                            detail="Solo se confirma una transferencia pendiente")

    pago.estado = "completado"
    pago.completado_en = datetime.now(timezone.utc)

    if pago.reserva is not None:
        pago.reserva.estado = "confirmada"
    if pago.inscripcion is not None:
        pago.inscripcion.estado = "aceptada"

    _notificar(db, pago.usuario_id, "Pago confirmado",
               f"Tu pago ({pago.concepto}) fue confirmado. Folio {pago.referencia}.")
    db.commit()
    db.refresh(pago)
    return pago
```

- [ ] **Step 4: Add the confirm endpoint**

En `api/app/routers/pagos.py`, añade el import de `require_roles` (cambiando la línea `from app.deps import get_current_user`):

```python
from app.deps import get_current_user, require_roles
```

Y añade el endpoint al final del archivo:

```python
@router.post("/{pago_id}/confirmar", response_model=PagoOut)
def confirmar_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    pago = db.get(models.Pago, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pagos_service.confirmar_pago(db, pago)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd api && python -m pytest tests/test_pagos_transferencia.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add api/app/pagos_service.py api/app/routers/pagos.py api/tests/test_pagos_transferencia.py
git commit -m "feat(pagos): transferencia con confirmacion del superadmin"
```

---

### Task 7: Inscripción de equipo a torneo (crear + listar)

**Files:**
- Create: `api/app/routers/inscripciones.py`
- Modify: `api/app/main.py` (registrar router)
- Test: `api/tests/test_inscripciones.py`

**Interfaces:**
- Consumes: `InscripcionCreate`, `InscripcionOut`.
- Produces:
  - `POST /inscripciones` → `InscripcionOut` (201)
  - `GET /inscripciones?torneo_id=` → `list[InscripcionOut]`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_inscripciones.py`:

```python
"""Inscripción de equipos a torneos (sin pago todavía: nace 'pendiente')."""


def _torneo(client, auth_admin, **over):
    body = {"nombre": "Copa Test", "sede_id": 1, "cuota_inscripcion": 500}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def test_entrenador_inscribe_su_equipo(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "pendiente"
    assert r.json()["torneo_nombre"] == "Copa Test"


def test_no_inscribe_equipo_ajeno(client, auth_admin):
    tid = _torneo(client, auth_admin)
    # jugador cualquiera intenta inscribir el equipo 1 (no es suyo)
    client.post("/auth/register", json={"nombre": "X", "correo": "x@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "x@demo.com", "password": "claveSegura123"}).json()["access_token"]
    r = client.post("/inscripciones", headers={"Authorization": f"Bearer {tok}"},
                    json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 403


def test_no_inscribe_dos_veces(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)
    client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 409


def test_no_inscribe_en_torneo_finalizado(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin, estado="finalizado")
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 409


def test_cupo_lleno_rechaza(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin, cupo_maximo=1)
    # equipo 1 ocupa el único cupo
    client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    # equipo 2 (mismo entrenador) ya no cabe
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 2})
    assert r.status_code == 409


def test_listar_inscripciones_por_torneo(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)
    client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    r = client.get(f"/inscripciones?torneo_id={tid}", headers=auth_admin)
    assert r.status_code == 200 and len(r.json()) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_inscripciones.py -v`
Expected: FAIL (404 en `/inscripciones`).

- [ ] **Step 3: Create the router**

Create `api/app/routers/inscripciones.py`:

```python
"""
Inscripción de equipos a torneos.

El entrenador dueño del equipo lo inscribe a un torneo. La inscripción nace
'pendiente'; pasa a 'aceptada' cuando se paga la cuota (router de pagos) — o
directo si el torneo no tiene cuota.

Reglas: el torneo no debe estar finalizado ni con inscripciones cerradas;
el equipo debe ser del entrenador; no se puede inscribir dos veces el mismo
equipo; se respeta el cupo máximo.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import InscripcionCreate, InscripcionOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


@router.post("", response_model=InscripcionOut, status_code=status.HTTP_201_CREATED)
def crear_inscripcion(
    datos: InscripcionCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    torneo = db.get(models.Torneo, datos.torneo_id)
    if torneo is None:
        raise HTTPException(status_code=400, detail="El torneo no existe")

    equipo = db.get(models.Equipo, datos.equipo_id)
    if equipo is None:
        raise HTTPException(status_code=400, detail="El equipo no existe")
    if not _es_admin(usuario) and equipo.entrenador_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo el entrenador del equipo puede inscribirlo")

    # Inscripciones abiertas
    if torneo.estado == "finalizado":
        raise HTTPException(status_code=409, detail="El torneo está finalizado")
    if torneo.fecha_cierre_inscripciones and date.today() > torneo.fecha_cierre_inscripciones:
        raise HTTPException(status_code=409, detail="Las inscripciones están cerradas")

    # No duplicar
    ya = (
        db.query(models.Inscripcion)
        .filter_by(torneo_id=datos.torneo_id, equipo_id=datos.equipo_id)
        .first()
    )
    if ya is not None:
        raise HTTPException(status_code=409, detail="El equipo ya está inscrito en este torneo")

    # Cupo
    if torneo.cupo_maximo is not None:
        inscritos = db.query(models.Inscripcion).filter_by(torneo_id=datos.torneo_id).count()
        if inscritos >= torneo.cupo_maximo:
            raise HTTPException(status_code=409, detail="El torneo llegó a su cupo máximo")

    inscripcion = models.Inscripcion(
        torneo_id=datos.torneo_id, equipo_id=datos.equipo_id, estado="pendiente",
    )
    db.add(inscripcion)
    db.commit()
    db.refresh(inscripcion)
    return inscripcion


@router.get("", response_model=list[InscripcionOut])
def listar_inscripciones(
    torneo_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Inscripcion)
    # Un entrenador ve las inscripciones de SUS equipos; el admin, todas.
    if not _es_admin(usuario):
        consulta = consulta.join(models.Equipo).filter(models.Equipo.entrenador_id == usuario.id)
    if torneo_id:
        consulta = consulta.filter(models.Inscripcion.torneo_id == torneo_id)
    return consulta.order_by(models.Inscripcion.id).all()
```

- [ ] **Step 4: Register the router in `main.py`**

En `api/app/main.py`, añade `inscripciones` a los imports de routers:

```python
from app.routers import (
    auth, torneos, reservas, partidos, estadisticas,
    sedes, canchas, usuarios, publico, solicitudes, equipos, invitaciones,
    notificaciones, jugador, pagos, inscripciones,
)
```

Y registra el router (después de `pagos`):

```python
app.include_router(inscripciones.router, prefix="/inscripciones", tags=["inscripciones"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd api && python -m pytest tests/test_inscripciones.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/inscripciones.py api/app/main.py api/tests/test_inscripciones.py
git commit -m "feat(inscripciones): crear y listar inscripciones de equipo a torneo"
```

---

### Task 8: Pago de inscripción

**Files:**
- Modify: `api/app/pagos_service.py` (añadir `pagar_inscripcion`)
- Modify: `api/app/routers/pagos.py` (añadir `POST /pagos/inscripcion/{id}`)
- Test: `api/tests/test_pagos_inscripcion.py`

**Interfaces:**
- Produces:
  - `pagos_service.pagar_inscripcion(db, usuario, inscripcion, datos, gateway=None) -> models.Pago`
  - Router `POST /pagos/inscripcion/{inscripcion_id}` → `PagoOut`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_inscripcion.py`:

```python
"""Pago de la cuota de inscripción a un torneo."""

TARJETA_OK = {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
              "cvv": "123", "titular": "Coach"}


def _torneo(client, auth_admin, **over):
    body = {"nombre": "Copa Pago", "sede_id": 1, "cuota_inscripcion": 500}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def _inscribir(client, auth_entrenador, tid, equipo_id=1):
    return client.post("/inscripciones", headers=auth_entrenador,
                       json={"torneo_id": tid, "equipo_id": equipo_id}).json()["id"]


def test_pago_inscripcion_tarjeta(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)
    iid = _inscribir(client, auth_entrenador, tid)
    r = client.post(f"/pagos/inscripcion/{iid}", headers=auth_entrenador,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 201, r.text
    assert r.json()["monto"] == 500.0
    assert r.json()["estado"] == "completado"
    ins = client.get(f"/inscripciones?torneo_id={tid}", headers=auth_entrenador).json()[0]
    assert ins["estado"] == "aceptada"


def test_no_paga_inscripcion_ajena(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)
    iid = _inscribir(client, auth_entrenador, tid)
    client.post("/auth/register", json={"nombre": "X", "correo": "x@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "x@demo.com", "password": "claveSegura123"}).json()["access_token"]
    r = client.post(f"/pagos/inscripcion/{iid}", headers={"Authorization": f"Bearer {tok}"},
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 403


def test_inscripcion_gratuita_no_requiere_pago(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin, cuota_inscripcion=0)
    iid = _inscribir(client, auth_entrenador, tid)
    r = client.post(f"/pagos/inscripcion/{iid}", headers=auth_entrenador,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_inscripcion.py -v`
Expected: FAIL (404 en `/pagos/inscripcion/...`).

- [ ] **Step 3: Add `pagar_inscripcion` to the service**

Añade al final de `api/app/pagos_service.py`:

```python
def pagar_inscripcion(db: Session, usuario: models.Usuario, inscripcion: models.Inscripcion,
                      datos: PagoCreate, gateway: PaymentGateway | None = None) -> models.Pago:
    gateway = gateway or _gateway

    if inscripcion.pago_id:
        previo = db.get(models.Pago, inscripcion.pago_id)
        if previo and previo.estado in ("completado", "pendiente"):
            raise HTTPException(status_code=409, detail="La inscripción ya tiene un pago en curso o completado")

    monto = calcular_monto_inscripcion(inscripcion.torneo)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="Esta inscripción no requiere pago")

    concepto = f"Inscripción {inscripcion.equipo.nombre} · {inscripcion.torneo.nombre}"
    pago, resultado = _procesar(db, usuario, monto, concepto, datos, gateway)

    if resultado.estado == "completado":
        inscripcion.pago_id = pago.id
        inscripcion.estado = "aceptada"
        _notificar(db, usuario.id, "Pago confirmado",
                   f"Tu {concepto} quedó pagada. Folio {pago.referencia}.")
    elif resultado.estado == "pendiente":
        inscripcion.pago_id = pago.id
        _notificar(db, usuario.id, "Pago en revisión",
                   f"Registramos tu transferencia por {concepto}. Pendiente de confirmación.")

    db.commit()
    if resultado.estado == "fallido":
        raise HTTPException(status_code=402, detail=resultado.motivo or "Pago rechazado")
    db.refresh(pago)
    return pago
```

- [ ] **Step 4: Add the endpoint**

En `api/app/routers/pagos.py`, añade el endpoint (después de `pagar_reserva`):

```python
@router.post("/inscripcion/{inscripcion_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_inscripcion(
    inscripcion_id: int,
    datos: PagoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    inscripcion = db.get(models.Inscripcion, inscripcion_id)
    if inscripcion is None:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    # Paga el entrenador dueño del equipo (o el admin)
    if not _es_admin(usuario) and inscripcion.equipo.entrenador_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una inscripción ajena")
    return pagos_service.pagar_inscripcion(db, usuario, inscripcion, datos)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd api && python -m pytest tests/test_pagos_inscripcion.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add api/app/pagos_service.py api/app/routers/pagos.py api/tests/test_pagos_inscripcion.py
git commit -m "feat(pagos): pago de inscripcion a torneo"
```

---

### Task 9: Historial, comprobante y recibo PDF

**Files:**
- Create: `api/app/recibo_pdf.py`
- Modify: `api/app/routers/pagos.py` (GET `/pagos`, GET `/pagos/{id}`, GET `/pagos/{id}/recibo.pdf`)
- Test: `api/tests/test_pagos_comprobante.py`

**Interfaces:**
- Consumes: `models.Pago`.
- Produces:
  - `recibo_pdf.generar(pago: models.Pago) -> bytes`
  - Router `GET /pagos`, `GET /pagos/{id}`, `GET /pagos/{id}/recibo.pdf`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_pagos_comprobante.py`:

```python
"""Historial, comprobante (JSON) y recibo PDF."""

TARJETA_OK = {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
              "cvv": "123", "titular": "Ana"}
RESERVA_BASE = {"cancha_id": 1, "fecha": "2026-08-05", "hora_inicio": "10:00", "hora_fin": "11:00"}


def _jugador(client, correo="ana@demo.com"):
    client.post("/auth/register", json={"nombre": "Ana", "correo": correo, "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": correo, "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _pagar(client, auth):
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]
    return client.post(f"/pagos/reserva/{rid}", headers=auth,
                       json={"metodo": "tarjeta", "tarjeta": TARJETA_OK}).json()


def test_historial_solo_muestra_lo_propio(client, auth_admin):
    ana = _jugador(client, "ana@demo.com")
    _pagar(client, ana)
    assert len(client.get("/pagos", headers=ana).json()) == 1
    # el admin ve todos
    assert len(client.get("/pagos", headers=auth_admin).json()) == 1


def test_comprobante_json(client):
    auth = _jugador(client)
    pago = _pagar(client, auth)
    r = client.get(f"/pagos/{pago['id']}", headers=auth)
    assert r.status_code == 200
    assert r.json()["concepto"].startswith("Reserva")
    assert r.json()["usuario_nombre"] == "Ana"


def test_no_ve_comprobante_ajeno(client):
    ana = _jugador(client, "ana@demo.com")
    luis = _jugador(client, "luis@demo.com")
    pago = _pagar(client, ana)
    assert client.get(f"/pagos/{pago['id']}", headers=luis).status_code == 403


def test_recibo_pdf_de_pago_completado(client):
    auth = _jugador(client)
    pago = _pagar(client, auth)
    r = client.get(f"/pagos/{pago['id']}/recibo.pdf", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_recibo_pdf_solo_si_completado(client, auth_admin):
    auth = _jugador(client)
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]
    pago = client.post(f"/pagos/reserva/{rid}", headers=auth, json={"metodo": "transferencia"}).json()
    # transferencia pendiente -> aún no hay recibo
    assert client.get(f"/pagos/{pago['id']}/recibo.pdf", headers=auth).status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_pagos_comprobante.py -v`
Expected: FAIL (404 en `/pagos` GET).

- [ ] **Step 3: Implement the PDF generator**

Create `api/app/recibo_pdf.py`:

```python
"""Genera el PDF del comprobante de pago (recibo simple)."""
from fpdf import FPDF

from app import models


def generar(pago: models.Pago) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Comprobante de Pago", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, "Sistema Integral de Canchas y Torneos", ln=True, align="C")
    pdf.ln(6)

    def fila(etiqueta, valor):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 9, f"{etiqueta}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 9, str(valor), ln=True)

    fila("Folio", pago.referencia or "-")
    fila("Concepto", pago.concepto or "-")
    fila("Titular", pago.usuario_nombre or "-")
    fila("Monto", f"$ {pago.monto:.2f}")
    fila("Método", pago.metodo)
    fila("Estado", pago.estado)
    fecha = pago.completado_en or pago.creado_en
    fila("Fecha", fecha.strftime("%Y-%m-%d %H:%M") if fecha else "-")

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 6, "Comprobante generado por el sistema. Pago simulado con fines "
                         "de demostración.")

    return bytes(pdf.output())
```

- [ ] **Step 4: Add the read endpoints**

En `api/app/routers/pagos.py`, añade el import de `Response` de FastAPI al inicio (junto a los demás imports de fastapi):

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
```

y el import del generador y del PagoOut ya existente:

```python
from app import models, pagos_service, recibo_pdf
```

Añade estos endpoints al final del archivo:

```python
@router.get("", response_model=list[PagoOut])
def historial_pagos(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Pago)
    if not _es_admin(usuario):
        consulta = consulta.filter(models.Pago.usuario_id == usuario.id)
    return consulta.order_by(models.Pago.id.desc()).all()


def _pago_visible(db: Session, pago_id: int, usuario: models.Usuario) -> models.Pago:
    pago = db.get(models.Pago, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if not _es_admin(usuario) and pago.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes ver un pago ajeno")
    return pago


@router.get("/{pago_id}", response_model=PagoOut)
def ver_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    return _pago_visible(db, pago_id, usuario)


@router.get("/{pago_id}/recibo.pdf")
def recibo(
    pago_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    pago = _pago_visible(db, pago_id, usuario)
    if pago.estado != "completado":
        raise HTTPException(status_code=409, detail="El recibo solo está disponible para pagos completados")
    contenido = recibo_pdf.generar(pago)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pago.id}.pdf"'},
    )
```

Nota: el endpoint `GET /{pago_id}` debe ir DESPUÉS de las rutas fijas `/reserva/{...}` e `/inscripcion/{...}` (ya lo están, pues estas se definieron antes). FastAPI casa por orden; `reserva`/`inscripcion` son literales y no chocan con `{pago_id}` numérico.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd api && python -m pytest tests/test_pagos_comprobante.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Run the full API suite**

Run: `cd api && python -m pytest -q`
Expected: todo verde (incluye los tests previos y los ~existentes).

- [ ] **Step 7: Commit**

```bash
git add api/app/recibo_pdf.py api/app/routers/pagos.py api/tests/test_pagos_comprobante.py
git commit -m "feat(pagos): historial, comprobante JSON y recibo PDF"
```

---

### Task 10: Móvil — pantalla de pago y comprobante

**Files:**
- Create: `mobile/src/screens/PagoScreen.js`
- Create: `mobile/src/screens/ComprobanteScreen.js`
- Modify: `mobile/src/api.js` (helper de descarga autenticada del PDF)
- Modify: `mobile/App.js` (registrar las dos pantallas en el navegador)
- Modify: `mobile/src/screens/player/ReservarScreen.js` (navegar a Pago tras crear la reserva)
- Modify: `mobile/package.json` (deps `expo-file-system`, `expo-sharing`)

**Interfaces:**
- Consumes: `apiPost`, `apiGet` de `mobile/src/api.js`; `API_URL`, `leerToken`.
- Produces: rutas de navegación `"Pago"` (params `{ tipo: "reserva"|"inscripcion", id }`) y `"Comprobante"` (params `{ pagoId }`).

> Nota: el frontend del repo no tiene tests automatizados. La verificación es manual con Expo (Step final).

- [ ] **Step 1: Add PDF download helper to `api.js`**

Añade al final de `mobile/src/api.js`:

```javascript
import * as FileSystem from "expo-file-system";

// Descarga el recibo PDF (autenticado) a un archivo local y devuelve su URI.
export async function descargarReciboPDF(pagoId) {
  const t = await leerToken();
  const destino = `${FileSystem.cacheDirectory}recibo_${pagoId}.pdf`;
  const { uri } = await FileSystem.downloadAsync(
    `${API_URL}/pagos/${pagoId}/recibo.pdf`,
    destino,
    { headers: { Authorization: `Bearer ${t}` } }
  );
  return uri;
}
```

- [ ] **Step 2: Create `PagoScreen.js`**

Create `mobile/src/screens/PagoScreen.js`:

```javascript
// Pantalla de pago reutilizable para reservas e inscripciones.
// Estilos autocontenidos (no depende de theme.js) para verse bien en el flujo claro.
import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert, ScrollView, StyleSheet,
} from "react-native";
import { apiPost } from "../api";

export default function PagoScreen({ route, navigation }) {
  const { tipo, id, resumen } = route.params; // tipo: "reserva" | "inscripcion"
  const [metodo, setMetodo] = useState("tarjeta");
  const [numero, setNumero] = useState("");
  const [expMes, setExpMes] = useState("");
  const [expAnio, setExpAnio] = useState("");
  const [cvv, setCvv] = useState("");
  const [titular, setTitular] = useState("");
  const [cargando, setCargando] = useState(false);

  async function pagar() {
    setCargando(true);
    try {
      const body = { metodo };
      if (metodo === "tarjeta") {
        body.tarjeta = {
          numero, cvv, titular,
          exp_mes: parseInt(expMes, 10),
          exp_anio: parseInt(expAnio, 10),
        };
      }
      const pago = await apiPost(`/pagos/${tipo}/${id}`, body);
      navigation.replace("Comprobante", { pagoId: pago.id });
    } catch (e) {
      Alert.alert("Pago no procesado", e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      <Text style={s.title}>Pago</Text>
      {resumen ? <Text style={s.resumen}>{resumen}</Text> : null}

      <View style={s.tabs}>
        {["tarjeta", "transferencia"].map((m) => (
          <TouchableOpacity key={m} onPress={() => setMetodo(m)} style={[s.tab, metodo === m && s.tabOn]}>
            <Text style={[s.tabTxt, metodo === m && s.tabTxtOn]}>
              {m === "tarjeta" ? "Tarjeta" : "Transferencia"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {metodo === "tarjeta" && (
        <>
          <TextInput style={s.input} placeholder="Número de tarjeta" keyboardType="number-pad"
            value={numero} onChangeText={setNumero} />
          <View style={{ flexDirection: "row" }}>
            <TextInput style={[s.input, { flex: 1, marginRight: 6 }]} placeholder="MM"
              keyboardType="number-pad" value={expMes} onChangeText={setExpMes} />
            <TextInput style={[s.input, { flex: 1, marginHorizontal: 6 }]} placeholder="AAAA"
              keyboardType="number-pad" value={expAnio} onChangeText={setExpAnio} />
            <TextInput style={[s.input, { flex: 1, marginLeft: 6 }]} placeholder="CVV"
              keyboardType="number-pad" value={cvv} onChangeText={setCvv} />
          </View>
          <TextInput style={s.input} placeholder="Titular" value={titular} onChangeText={setTitular} />
        </>
      )}

      {metodo === "transferencia" && (
        <Text style={s.nota}>
          Se registrará tu pago por transferencia. Quedará pendiente hasta que un
          administrador lo confirme.
        </Text>
      )}

      <TouchableOpacity style={s.btn} onPress={pagar} disabled={cargando}>
        {cargando ? <ActivityIndicator color="#fff" /> : <Text style={s.btnTxt}>Pagar</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f4f6f5" },
  content: { padding: 20 },
  title: { fontSize: 24, fontWeight: "800", color: "#0f2c1b", marginBottom: 6 },
  resumen: { color: "#4b5f54", fontSize: 14, marginBottom: 8 },
  tabs: { flexDirection: "row", marginVertical: 12 },
  tab: { flex: 1, padding: 12, marginHorizontal: 4, borderRadius: 8, backgroundColor: "#e5e7eb" },
  tabOn: { backgroundColor: "#1f7a44" },
  tabTxt: { textAlign: "center", color: "#111", fontWeight: "700" },
  tabTxtOn: { color: "#fff" },
  input: {
    backgroundColor: "#fff", borderColor: "#d3dbd6", borderWidth: 1, borderRadius: 10,
    color: "#111", paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, marginBottom: 12,
  },
  nota: { color: "#4b5f54", fontSize: 14, marginBottom: 12 },
  btn: { backgroundColor: "#1f7a44", borderRadius: 10, paddingVertical: 15, alignItems: "center", marginTop: 6 },
  btnTxt: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
```

- [ ] **Step 3: Create `ComprobanteScreen.js`**

Create `mobile/src/screens/ComprobanteScreen.js`:

```javascript
// Comprobante de pago + descarga del PDF. Estilos autocontenidos.
import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, Alert, StyleSheet } from "react-native";
import * as Sharing from "expo-sharing";
import { apiGet, descargarReciboPDF } from "../api";

export default function ComprobanteScreen({ route }) {
  const { pagoId } = route.params;
  const [pago, setPago] = useState(null);

  useEffect(() => {
    apiGet(`/pagos/${pagoId}`).then(setPago).catch((e) => Alert.alert("Error", e.message));
  }, [pagoId]);

  async function descargar() {
    try {
      const uri = await descargarReciboPDF(pagoId);
      if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(uri);
    } catch (e) {
      Alert.alert("No se pudo generar el recibo", e.message);
    }
  }

  if (!pago) return <ActivityIndicator style={{ marginTop: 40 }} />;

  const fila = (k, v) => (
    <View style={s.fila}>
      <Text style={s.k}>{k}</Text>
      <Text style={s.v}>{v}</Text>
    </View>
  );

  return (
    <View style={s.screen}>
      <Text style={s.title}>Comprobante</Text>
      {fila("Folio", pago.referencia || "-")}
      {fila("Concepto", pago.concepto || "-")}
      {fila("Monto", `$ ${Number(pago.monto).toFixed(2)}`)}
      {fila("Método", pago.metodo)}
      {fila("Estado", pago.estado)}
      {pago.estado === "completado" && (
        <TouchableOpacity style={s.btn} onPress={descargar}>
          <Text style={s.btnTxt}>Descargar PDF</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f4f6f5", padding: 20 },
  title: { fontSize: 24, fontWeight: "800", color: "#0f2c1b", marginBottom: 12 },
  fila: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8, borderBottomColor: "#e2e8e4", borderBottomWidth: 1 },
  k: { fontWeight: "700", color: "#0f2c1b" },
  v: { color: "#4b5f54" },
  btn: { backgroundColor: "#1f7a44", borderRadius: 10, paddingVertical: 15, alignItems: "center", marginTop: 20 },
  btnTxt: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
```

- [ ] **Step 4: Register screens and add dependencies**

En `mobile/App.js`, añade los imports junto a los demás de pantallas (por ejemplo, justo después de `import RefHistoryScreen from "./src/screens/referee/RefHistoryScreen";`):

```javascript
import PagoScreen from "./src/screens/PagoScreen";
import ComprobanteScreen from "./src/screens/ComprobanteScreen";
```

Y registra las dos pantallas dentro del `<Stack.Navigator>`, justo después de la línea del `Stack.Screen` de `Notifications` (usa `greenHeader`, que ya está definido en el archivo):

```javascript
          <Stack.Screen name="Pago" component={PagoScreen} options={{ ...greenHeader, title: "PAGO" }} />
          <Stack.Screen name="Comprobante" component={ComprobanteScreen} options={{ ...greenHeader, title: "COMPROBANTE" }} />
```

Instala las dependencias:

```bash
cd mobile && npx expo install expo-file-system expo-sharing
```

- [ ] **Step 5: Wire from `ReservarScreen`**

`ReservarScreen` es una pestaña y NO recibe `navigation` como prop: hay que obtenerlo con `useNavigation`. Tres cambios en `mobile/src/screens/player/ReservarScreen.js`:

1. Añade el import (después de la línea `import { lp, ls } from "../../publicTheme";`):

```javascript
import { useNavigation } from "@react-navigation/native";
```

2. Dentro del componente, justo después de `const dias = proximosDias();`:

```javascript
  const navigation = useNavigation();
```

3. En `reservar()`, reemplaza el bloque del `try` que hoy es:

```javascript
      await apiPost("/reservas", { cancha_id: canchaSel.id, fecha: fechaSel, hora_inicio: horaSel, hora_fin: finH });
      Alert.alert("Reserva creada", `${canchaSel.nombre} · ${fechaSel} · ${horaSel}. Queda pendiente de pago.`);
      setHoraSel(null);
      setOcupados((o) => [...o, horaSel]);
```

por:

```javascript
      const r = await apiPost("/reservas", { cancha_id: canchaSel.id, fecha: fechaSel, hora_inicio: horaSel, hora_fin: finH });
      setHoraSel(null);
      setOcupados((o) => [...o, horaSel]);
      navigation.navigate("Pago", {
        tipo: "reserva",
        id: r.id,
        resumen: `Reserva ${canchaSel.nombre} · ${fechaSel} · ${horaSel}`,
      });
```

- [ ] **Step 6 (opcional): Wire coach "Inscribir equipo"**

La misma `PagoScreen` sirve para inscripciones. En la pantalla de detalle de torneo del entrenador, el botón "Inscribir equipo" sigue el patrón: crear la inscripción y navegar a Pago con `tipo: "inscripcion"`.

```javascript
const ins = await apiPost("/inscripciones", { torneo_id: torneoId, equipo_id: equipoId });
navigation.navigate("Pago", { tipo: "inscripcion", id: ins.id, resumen: `Inscripción · ${torneoNombre}` });
```

- [ ] **Step 7: Manual verification (Expo)**

```bash
cd mobile && npx expo start
```

Verifica el flujo: crear una reserva → pantalla de Pago → pagar con tarjeta `4111 1111 1111 1234` → Comprobante con estado "completado" → "Descargar PDF" abre el diálogo de compartir. Prueba también `...0000` (rechazo) y transferencia (queda pendiente).

- [ ] **Step 8: Commit**

```bash
git add mobile/src/screens/PagoScreen.js mobile/src/screens/ComprobanteScreen.js mobile/src/api.js mobile/App.js mobile/src/screens/player/ReservarScreen.js mobile/package.json mobile/package-lock.json
git commit -m "feat(pagos): pantalla de pago y comprobante en la app movil"
```

---

### Task 11: Panel web — confirmar transferencias

**Files:**
- Modify: `web/app/app.py` (rutas `/pagos` y `/pagos/<id>/confirmar`)
- Create: `web/app/templates/pagos.html`
- Modify: `web/app/templates/base.html` (enlace en el menú)

**Interfaces:**
- Consumes: helpers `api_get`, `api_post`, `login_required` de `web/app/app.py`; endpoints `GET /pagos` y `POST /pagos/{id}/confirmar` de la API.

> Nota: el panel Flask no tiene tests automatizados en el repo. Verificación manual (Step final).

- [ ] **Step 1: Add the routes**

En `web/app/app.py`, añade (siguiendo el estilo de las demás vistas, p. ej. `reservas`):

```python
@app.route("/pagos")
@login_required
def pagos():
    r = api_get("/pagos")
    lista = r.json() if r.status_code == 200 else []
    # Solo interesan las transferencias pendientes para confirmar; el resto, informativo
    pendientes = [p for p in lista if p["metodo"] == "transferencia" and p["estado"] == "pendiente"]
    return render_template("pagos.html", pagos=lista, pendientes=pendientes, active="pagos")


@app.route("/pagos/<int:pago_id>/confirmar", methods=["POST"])
@login_required
def pago_confirmar(pago_id):
    r = api_post(f"/pagos/{pago_id}/confirmar", {})
    if r.status_code == 200:
        flash("Pago confirmado.", "ok")
    else:
        flash(_detalle_error(r), "error")
    return redirect(url_for("pagos"))
```

- [ ] **Step 2: Create the template**

Create `web/app/templates/pagos.html` (extiende `base.html`; usa los bloques reales `title`, `heading` y `content`):

```html
{% extends "base.html" %}
{% block title %}Pagos{% endblock %}
{% block heading %}Pagos{% endblock %}
{% block content %}

<h2>Transferencias pendientes de confirmar</h2>
{% if pendientes %}
<table>
  <thead><tr><th>Folio</th><th>Concepto</th><th>Titular</th><th>Monto</th><th></th></tr></thead>
  <tbody>
    {% for p in pendientes %}
    <tr>
      <td>{{ p.referencia }}</td>
      <td>{{ p.concepto }}</td>
      <td>{{ p.usuario_nombre }}</td>
      <td>$ {{ '%.2f'|format(p.monto) }}</td>
      <td>
        <form method="post" action="{{ url_for('pago_confirmar', pago_id=p.id) }}">
          <button type="submit">Confirmar</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
<p>No hay transferencias pendientes.</p>
{% endif %}

<h2>Todos los pagos</h2>
<table>
  <thead><tr><th>Folio</th><th>Concepto</th><th>Método</th><th>Monto</th><th>Estado</th></tr></thead>
  <tbody>
    {% for p in pagos %}
    <tr>
      <td>{{ p.referencia }}</td>
      <td>{{ p.concepto }}</td>
      <td>{{ p.metodo }}</td>
      <td>$ {{ '%.2f'|format(p.monto) }}</td>
      <td>{{ p.estado }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Add the menu link**

En `web/app/templates/base.html`, dentro de `<nav class="nav">`, añade el enlace después del de Reservas (línea con `url_for('reservas')`), siguiendo el mismo patrón con `dot` y clase `active`:

```html
        <a href="{{ url_for('pagos') }}" class="{{ 'active' if active == 'pagos' }}"><span class="dot"></span> Pagos</a>
```

- [ ] **Step 4: Manual verification**

```bash
docker compose up --build
```

Entra al panel (`http://localhost:5000`) como `superadmin@demo.com / admin1234`, genera una transferencia desde la app o `curl`, ve a "Pagos" y confírmala. Verifica que la reserva/inscripción pase a confirmada/aceptada.

- [ ] **Step 5: Commit**

```bash
git add web/app/app.py web/app/templates/pagos.html web/app/templates/base.html
git commit -m "feat(pagos): panel web para confirmar transferencias"
```

---

## Cierre

- [ ] **Suite completa verde:** `cd api && python -m pytest -q`
- [ ] **Actualizar `.env.example`:** el bloque de Pagos ya existe (STRIPE_*); no requiere cambios para el mock.
- [ ] Preparar PR de la rama `feature/modulo-pagos` cuando el usuario lo indique.
