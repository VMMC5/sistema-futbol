"""Pruebas del módulo de canchas."""


def _jugador(client):
    client.post("/auth/register", json={"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_listar_canchas_incluye_la_sembrada(client, auth_admin):
    r = client.get("/canchas", headers=auth_admin)
    assert r.status_code == 200
    assert any(c["nombre"] == "Cancha 1" for c in r.json())


def test_listar_requiere_token(client):
    assert client.get("/canchas").status_code == 401


def test_admin_crea_cancha_con_sede_nombre(client, auth_admin):
    r = client.post("/canchas", headers=auth_admin, json={
        "sede_id": 1, "nombre": "Cancha 2", "tipo": "futbol 11", "precio_hora": 500,
    })
    assert r.status_code == 201
    assert r.json()["sede_nombre"] == "Sede Central"   # nombre de la sede incluido


def test_crear_con_sede_inexistente(client, auth_admin):
    r = client.post("/canchas", headers=auth_admin, json={"sede_id": 999, "nombre": "X"})
    assert r.status_code == 400


def test_tipo_invalido_rechazado(client, auth_admin):
    r = client.post("/canchas", headers=auth_admin, json={"sede_id": 1, "nombre": "X", "tipo": "futbol 9"})
    assert r.status_code == 422


def test_jugador_no_crea_cancha(client):
    auth = _jugador(client)
    assert client.post("/canchas", headers=auth, json={"sede_id": 1, "nombre": "X"}).status_code == 403


def test_admin_actualiza_cancha(client, auth_admin):
    cid = client.post("/canchas", headers=auth_admin, json={"sede_id": 1, "nombre": "Cancha 3"}).json()["id"]
    r = client.put(f"/canchas/{cid}", headers=auth_admin, json={"disponible": False, "precio_hora": 300})
    assert r.status_code == 200
    assert r.json()["disponible"] is False and r.json()["precio_hora"] == 300


def test_eliminar_cancha_sin_dependencias(client, auth_admin):
    cid = client.post("/canchas", headers=auth_admin, json={"sede_id": 1, "nombre": "Temporal"}).json()["id"]
    assert client.delete(f"/canchas/{cid}", headers=auth_admin).status_code == 204


def test_no_eliminar_cancha_con_partido(client, auth_admin, torneo_id):
    # Crear un partido en la cancha #1 -> ya no se puede borrar
    client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2, "cancha_id": 1,
    })
    assert client.delete("/canchas/1", headers=auth_admin).status_code == 409
