"""Pruebas del plan de alineación con formaciones (panel del entrenador)."""


def _partido(client, auth_admin, torneo_id):
    return client.post("/partidos", headers=auth_admin,
                       json={"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}).json()["id"]


def _roster(client, auth_entrenador, equipo_id=1):
    # Reemplaza la plantilla del equipo y devuelve los jugadores creados (con id)
    r = client.put(f"/equipos/{equipo_id}", headers=auth_entrenador, json={
        "nombre": "Equipo A", "jugadores": [
            {"nombre": "Portero", "posicion": "POR", "dorsal": 1},
            {"nombre": "Delantero", "posicion": "DEL", "dorsal": 9},
        ],
    })
    return r.json()["jugadores"]


def test_plan_por_defecto_vacio(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    r = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.json()["formacion"] == "4-4-2" and r.json()["jugadores"] == []


def test_guardar_y_leer_plan(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    jug = _roster(client, auth_entrenador)
    cuerpo = {
        "equipo_id": 1, "formacion": "4-3-3",
        "jugadores": [
            {"jugador_equipo_id": jug[0]["id"], "posicion": "POR", "orden": 0},
            {"jugador_equipo_id": jug[1]["id"], "posicion": "DEL", "orden": 9},
        ],
    }
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json=cuerpo)
    assert r.status_code == 200
    d = r.json()
    assert d["formacion"] == "4-3-3" and len(d["jugadores"]) == 2
    # Toma el snapshot de nombre y dorsal de la plantilla
    porteros = [j for j in d["jugadores"] if j["posicion"] == "POR"]
    assert porteros[0]["nombre"] == "Portero" and porteros[0]["dorsal"] == 1

    # Persistió
    r2 = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_entrenador)
    assert r2.json()["formacion"] == "4-3-3" and len(r2.json()["jugadores"]) == 2


def test_jugador_de_otro_equipo_rechazado(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    jug = _roster(client, auth_entrenador)
    # Plantilla del equipo 2
    otro = client.put("/equipos/2", headers=auth_entrenador, json={
        "nombre": "Equipo B", "jugadores": [{"nombre": "Ajeno"}]}).json()["jugadores"][0]
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": otro["id"], "posicion": "POR", "orden": 0}]})
    assert r.status_code == 400


def test_jugador_repetido_rechazado(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    jug = _roster(client, auth_entrenador)
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [
            {"jugador_equipo_id": jug[0]["id"], "posicion": "POR", "orden": 0},
            {"jugador_equipo_id": jug[0]["id"], "posicion": "DEF", "orden": 1},
        ]})
    assert r.status_code == 400


def test_equipo_no_juega_el_partido(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    nuevo = client.post("/equipos", headers=auth_entrenador, json={"nombre": "Fuera"}).json()["id"]
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": nuevo, "formacion": "4-4-2", "jugadores": []})
    assert r.status_code == 400


def test_no_se_edita_si_ya_inicio(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_admin)  # admin puede iniciar
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2", "jugadores": []})
    assert r.status_code == 409


def test_mis_partidos_entrenador(client, auth_admin, auth_entrenador, torneo_id):
    _partido(client, auth_admin, torneo_id)
    r = client.get("/equipos/mis-partidos", headers=auth_entrenador)
    assert r.status_code == 200 and len(r.json()) >= 1
    assert r.json()[0]["mi_equipo_id"] in (1, 2) and "rival_nombre" in r.json()[0]
