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


def test_no_confirma_transferencia_de_reserva_cancelada(client, auth_admin):
    auth = _jugador(client)
    rid = client.post("/reservas", headers=auth, json=RESERVA_BASE).json()["id"]
    pago = client.post(f"/pagos/reserva/{rid}", headers=auth, json={"metodo": "transferencia"}).json()
    assert client.post(f"/reservas/{rid}/cancelar", headers=auth).status_code == 200
    r = client.post(f"/pagos/{pago['id']}/confirmar", headers=auth_admin)
    assert r.status_code == 409
    # la reserva sigue cancelada (no resucitó)
    assert client.get(f"/reservas/{rid}", headers=auth).json()["estado"] == "cancelada"
