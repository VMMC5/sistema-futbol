"""Pruebas del panel del entrenador: equipos, plantilla, resumen y stats."""


def _mis_equipos(client, auth):
    return client.get("/equipos", headers=auth).json()


def test_entrenador_ve_solo_sus_equipos(client, auth_entrenador, auth_admin):
    mios = _mis_equipos(client, auth_entrenador)
    assert len(mios) == 2  # Equipo A y B (seed)
    # El admin ve todos
    assert len(_mis_equipos(client, auth_admin)) >= 2


def test_crear_equipo_con_plantilla(client, auth_entrenador):
    r = client.post("/equipos", headers=auth_entrenador, json={
        "nombre": "Halcones FC", "color": "Rojo", "categoria": "Liga A",
        "jugadores": [
            {"nombre": "J. Ramírez", "posicion": "Delantero", "dorsal": 9},
            {"nombre": "L. González", "posicion": "Portero", "dorsal": 1},
        ],
    })
    assert r.status_code == 201
    d = r.json()
    assert d["jugadores_count"] == 2 and d["categoria"] == "Liga A"
    assert {j["nombre"] for j in d["jugadores"]} == {"J. Ramírez", "L. González"}


def test_actualizar_reemplaza_plantilla(client, auth_entrenador):
    eid = client.post("/equipos", headers=auth_entrenador, json={
        "nombre": "Temp", "jugadores": [{"nombre": "A"}, {"nombre": "B"}],
    }).json()["id"]

    r = client.put(f"/equipos/{eid}", headers=auth_entrenador, json={
        "nombre": "Temp FC", "jugadores": [{"nombre": "Solo Uno", "dorsal": 7}],
    })
    assert r.status_code == 200
    assert r.json()["nombre"] == "Temp FC" and r.json()["jugadores_count"] == 1


def test_agregar_y_quitar_jugador(client, auth_entrenador):
    eid = client.post("/equipos", headers=auth_entrenador, json={"nombre": "Roster FC"}).json()["id"]

    r = client.post(f"/equipos/{eid}/jugadores", headers=auth_entrenador,
                    json={"nombre": "Nuevo", "posicion": "Medio", "dorsal": 8})
    assert r.status_code == 201 and r.json()["jugadores_count"] == 1
    je_id = r.json()["jugadores"][0]["id"]

    r = client.delete(f"/equipos/{eid}/jugadores/{je_id}", headers=auth_entrenador)
    assert r.status_code == 200 and r.json()["jugadores_count"] == 0


def test_no_puede_ver_equipo_ajeno(client, auth_entrenador, auth_admin):
    # El admin crea un equipo (queda a su nombre)
    ajeno = client.post("/equipos", headers=auth_admin, json={"nombre": "Del Admin"}).json()["id"]
    # El entrenador no debe poder verlo
    assert client.get(f"/equipos/{ajeno}", headers=auth_entrenador).status_code == 403


def test_resumen_entrenador(client, auth_entrenador):
    r = client.get("/equipos/resumen", headers=auth_entrenador)
    assert r.status_code == 200
    d = r.json()
    assert d["equipos_count"] == 2 and d["equipo_principal"] is not None
    assert "proximo_partido" in d


def test_estadisticas_equipo(client, auth_entrenador):
    eid = _mis_equipos(client, auth_entrenador)[0]["id"]
    r = client.get(f"/equipos/{eid}/estadisticas", headers=auth_entrenador)
    assert r.status_code == 200
    for k in ["pj", "pg", "pe", "pp", "posicion", "goleadores"]:
        assert k in r.json()


def test_borrar_equipo_sin_dependencias(client, auth_entrenador):
    eid = client.post("/equipos", headers=auth_entrenador, json={"nombre": "Borrable"}).json()["id"]
    assert client.delete(f"/equipos/{eid}", headers=auth_entrenador).status_code == 204
    assert client.get(f"/equipos/{eid}", headers=auth_entrenador).status_code == 404
