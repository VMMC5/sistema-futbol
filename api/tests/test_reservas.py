"""
Pruebas del módulo de reservas.

Cubren la regla de negocio (no solapar horarios) y el control de propiedad
(cada quien gestiona solo sus reservas; el admin, todas).
"""


def _jugador(client, correo="ana@demo.com"):
    """Registra un jugador y devuelve su cabecera de autorización."""
    client.post("/auth/register", json={
        "nombre": "Jugador", "correo": correo, "password": "claveSegura123",
    })
    tok = client.post("/auth/login", json={"correo": correo, "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


RESERVA_BASE = {"cancha_id": 1, "fecha": "2026-07-01", "hora_inicio": "10:00", "hora_fin": "11:00"}


# ---------- Creación y validaciones ----------
def test_crear_reserva_ok(client):
    auth = _jugador(client)
    r = client.post("/reservas", headers=auth, json=RESERVA_BASE)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"


def test_reserva_sin_token(client):
    assert client.post("/reservas", json=RESERVA_BASE).status_code == 401


def test_cancha_inexistente(client):
    auth = _jugador(client)
    r = client.post("/reservas", headers=auth, json={**RESERVA_BASE, "cancha_id": 999})
    assert r.status_code == 400


def test_hora_fin_antes_de_inicio(client):
    auth = _jugador(client)
    r = client.post("/reservas", headers=auth, json={
        **RESERVA_BASE, "hora_inicio": "11:00", "hora_fin": "10:00",
    })
    assert r.status_code == 422


# ---------- Regla de solapamiento ----------
def test_solapamiento_rechazado(client):
    auth = _jugador(client)
    assert client.post("/reservas", headers=auth, json=RESERVA_BASE).status_code == 201
    # 10:30-11:30 se solapa con 10:00-11:00 -> 409
    r = client.post("/reservas", headers=auth, json={
        **RESERVA_BASE, "hora_inicio": "10:30", "hora_fin": "11:30",
    })
    assert r.status_code == 409


def test_horarios_contiguos_si_permitidos(client):
    auth = _jugador(client)
    assert client.post("/reservas", headers=auth, json=RESERVA_BASE).status_code == 201
    # 11:00-12:00 empieza justo cuando termina la anterior -> permitido
    r = client.post("/reservas", headers=auth, json={
        **RESERVA_BASE, "hora_inicio": "11:00", "hora_fin": "12:00",
    })
    assert r.status_code == 201


def test_otro_dia_no_choca(client):
    auth = _jugador(client)
    assert client.post("/reservas", headers=auth, json=RESERVA_BASE).status_code == 201
    r = client.post("/reservas", headers=auth, json={**RESERVA_BASE, "fecha": "2026-07-02"})
    assert r.status_code == 201


def test_cancelar_libera_el_horario(client):
    auth = _jugador(client)
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]
    # Mismo horario choca...
    assert client.post("/reservas", headers=auth, json=RESERVA_BASE).status_code == 409
    # ...pero al cancelar la primera, el horario queda libre
    assert client.post(f"/reservas/{rid}/cancelar", headers=auth).status_code == 200
    assert client.post("/reservas", headers=auth, json=RESERVA_BASE).status_code == 201


# ---------- Propiedad y roles ----------
def test_usuario_solo_ve_sus_reservas(client, auth_admin):
    ana = _jugador(client, "ana@demo.com")
    luis = _jugador(client, "luis@demo.com")
    client.post("/reservas", headers=ana, json=RESERVA_BASE)
    client.post("/reservas", headers=luis, json={**RESERVA_BASE, "fecha": "2026-07-03"})

    assert len(client.get("/reservas", headers=ana).json()) == 1   # solo la suya
    assert len(client.get("/reservas", headers=luis).json()) == 1  # solo la suya
    assert len(client.get("/reservas", headers=auth_admin).json()) == 2  # admin ve todas


def test_no_puede_cancelar_reserva_ajena(client):
    ana = _jugador(client, "ana@demo.com")
    luis = _jugador(client, "luis@demo.com")
    rid = client.post("/reservas", headers=ana, json=RESERVA_BASE).json()["id"]
    assert client.post(f"/reservas/{rid}/cancelar", headers=luis).status_code == 403


def test_solo_admin_confirma(client, auth_admin):
    ana = _jugador(client, "ana@demo.com")
    rid = client.post("/reservas", headers=ana, json=RESERVA_BASE).json()["id"]
    assert client.post(f"/reservas/{rid}/confirmar", headers=ana).status_code == 403
    r = client.post(f"/reservas/{rid}/confirmar", headers=auth_admin)
    assert r.status_code == 200 and r.json()["estado"] == "confirmada"
