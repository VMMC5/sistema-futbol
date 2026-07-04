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
    client.post("/auth/register", json={"nombre": "Player X", "correo": "x@demo.com", "password": "claveSegura123"})
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
