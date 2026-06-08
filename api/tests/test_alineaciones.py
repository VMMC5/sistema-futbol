"""
Pruebas de alineaciones (cierre del módulo de partidos).

Datos sembrados (ver conftest):
- equipos id=1 (A) e id=2 (B); el jugador 'miembro' pertenece al Equipo A.
- entrenador (fixture auth_entrenador) es el técnico de ambos equipos de prueba.
"""


def _crear_partido(client, auth_admin, torneo_id, arbitro_id=None):
    cuerpo = {"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}
    if arbitro_id:
        cuerpo["arbitro_id"] = arbitro_id
    return client.post("/partidos", headers=auth_admin, json=cuerpo).json()["id"]


def test_entrenador_alinea_jugador_de_su_equipo(client, auth_admin, auth_entrenador, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    r = client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json={
        "equipo_id": 1, "jugador_id": miembro_id, "posicion": "delantero",
    })
    assert r.status_code == 201
    assert r.json()["titular"] is True


def test_no_se_puede_alinear_jugador_ajeno_al_equipo(client, auth_admin, auth_entrenador, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    # Un jugador recién registrado NO pertenece al Equipo A
    client.post("/auth/register", json={"nombre": "Foraneo", "correo": "for@demo.com", "password": "claveSegura123"})
    fid = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer " + client.post(
            "/auth/login", json={"correo": "for@demo.com", "password": "claveSegura123"}
        ).json()["access_token"]},
    ).json()["id"]

    r = client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json={
        "equipo_id": 1, "jugador_id": fid,
    })
    assert r.status_code == 400


def test_equipo_que_no_juega_rechazado(client, auth_admin, auth_entrenador, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    r = client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json={
        "equipo_id": 99, "jugador_id": miembro_id,
    })
    assert r.status_code == 400


def test_jugador_no_puede_armar_alineacion(client, auth_admin, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    # Login como el propio jugador 'miembro' (no es entrenador ni admin)
    tok = client.post("/auth/login", json={"correo": "miembro@demo.com", "password": "miembropass123"}).json()["access_token"]
    r = client.post(f"/partidos/{pid}/alineacion", headers={"Authorization": f"Bearer {tok}"}, json={
        "equipo_id": 1, "jugador_id": miembro_id,
    })
    assert r.status_code == 403


def test_no_repetir_jugador_en_alineacion(client, auth_admin, auth_entrenador, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    cuerpo = {"equipo_id": 1, "jugador_id": miembro_id}
    assert client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json=cuerpo).status_code == 201
    # Segunda vez -> 409
    assert client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json=cuerpo).status_code == 409


def test_no_se_modifica_alineacion_tras_iniciar(client, auth_admin, auth_entrenador, auth_arbitro, arbitro_id, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    # Ya está en juego -> no se puede tocar la alineación
    r = client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json={
        "equipo_id": 1, "jugador_id": miembro_id,
    })
    assert r.status_code == 409


def test_listar_y_quitar_de_alineacion(client, auth_admin, auth_entrenador, miembro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id)
    aid = client.post(f"/partidos/{pid}/alineacion", headers=auth_entrenador, json={
        "equipo_id": 1, "jugador_id": miembro_id,
    }).json()["id"]

    assert len(client.get(f"/partidos/{pid}/alineacion", headers=auth_admin).json()) == 1
    assert client.delete(f"/partidos/{pid}/alineacion/{aid}", headers=auth_entrenador).status_code == 204
    assert len(client.get(f"/partidos/{pid}/alineacion", headers=auth_admin).json()) == 0
