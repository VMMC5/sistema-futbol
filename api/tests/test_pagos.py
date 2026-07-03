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
