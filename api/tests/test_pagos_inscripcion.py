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
    client.post("/auth/register", json={"nombre": "XX", "correo": "x@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "x@demo.com", "password": "claveSegura123"}).json()["access_token"]
    r = client.post(f"/pagos/inscripcion/{iid}", headers={"Authorization": f"Bearer {tok}"},
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 403


def test_inscripcion_gratuita_queda_aceptada(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin, cuota_inscripcion=0)
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 201
    assert r.json()["estado"] == "aceptada"


def test_no_paga_inscripcion_no_pendiente(client, db_session, auth_admin, auth_entrenador):
    from app import models
    tid = _torneo(client, auth_admin)
    iid = _inscribir(client, auth_entrenador, tid)
    db = db_session()
    ins = db.get(models.Inscripcion, iid)
    ins.estado = "rechazada"      # estado no-pendiente sin pago (solo alcanzable a nivel de datos)
    db.commit()
    r = client.post(f"/pagos/inscripcion/{iid}", headers=auth_entrenador,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 409
