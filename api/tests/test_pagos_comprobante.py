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
    luis = _jugador(client, "luis@demo.com")
    rid = client.post("/reservas", headers=luis, json={**RESERVA_BASE, "fecha": "2026-08-09"}).json()["id"]
    client.post(f"/pagos/reserva/{rid}", headers=luis, json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert len(client.get("/pagos", headers=ana).json()) == 1
    assert len(client.get("/pagos", headers=luis).json()) == 1
    # el admin ve todos
    assert len(client.get("/pagos", headers=auth_admin).json()) >= 2


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


def test_recibo_pdf_con_texto_no_latin1(client, db_session):
    from app import models
    auth = _jugador(client)
    pago = _pagar(client, auth)               # pago con tarjeta -> completado
    db = db_session()
    p = db.get(models.Pago, pago["id"])
    p.concepto = "Reserva 🏟️ Cancha ✅"       # caracteres fuera de Latin-1
    db.commit()
    r = client.get(f"/pagos/{pago['id']}/recibo.pdf", headers=auth)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
