"""Pruebas del módulo de sedes."""


def _jugador(client):
    client.post("/auth/register", json={"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_listar_sedes_incluye_la_sembrada(client, auth_admin):
    r = client.get("/sedes", headers=auth_admin)
    assert r.status_code == 200
    assert any(s["nombre"] == "Sede Central" for s in r.json())


def test_listar_requiere_token(client):
    assert client.get("/sedes").status_code == 401


def test_admin_crea_sede(client, auth_admin):
    r = client.post("/sedes", headers=auth_admin, json={"nombre": "Sede Norte", "ciudad": "Pachuca"})
    assert r.status_code == 201
    assert r.json()["nombre"] == "Sede Norte"


def test_jugador_no_crea_sede(client):
    auth = _jugador(client)
    r = client.post("/sedes", headers=auth, json={"nombre": "Sede X"})
    assert r.status_code == 403


def test_ver_sede_inexistente(client, auth_admin):
    assert client.get("/sedes/999", headers=auth_admin).status_code == 404


def test_admin_actualiza_sede(client, auth_admin):
    sid = client.post("/sedes", headers=auth_admin, json={"nombre": "Sede Sur"}).json()["id"]
    r = client.put(f"/sedes/{sid}", headers=auth_admin, json={"ciudad": "Tula"})
    assert r.status_code == 200 and r.json()["ciudad"] == "Tula"


def test_eliminar_sede_sin_dependencias(client, auth_admin):
    sid = client.post("/sedes", headers=auth_admin, json={"nombre": "Sede Temporal"}).json()["id"]
    assert client.delete(f"/sedes/{sid}", headers=auth_admin).status_code == 204


def test_no_eliminar_sede_con_cancha(client, auth_admin):
    # La sede #1 (sembrada) tiene una cancha asociada -> 409
    assert client.delete("/sedes/1", headers=auth_admin).status_code == 409


def test_jugador_no_actualiza_sede(client):
    auth = _jugador(client)
    assert client.put("/sedes/1", headers=auth, json={"ciudad": "X"}).status_code == 403


def test_actualizar_sede_inexistente(client, auth_admin):
    assert client.put("/sedes/999", headers=auth_admin, json={"ciudad": "X"}).status_code == 404
