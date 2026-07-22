"""Pruebas del plan de alineación con formaciones (panel del entrenador)."""


def _partido(client, auth_admin, torneo_id):
    return client.post("/partidos", headers=auth_admin,
                       json={"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}).json()["id"]


def test_plan_por_defecto_vacio(client, auth_admin, auth_entrenador, torneo_id):
    pid = _partido(client, auth_admin, torneo_id)
    r = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.json()["formacion"] == "4-4-2" and r.json()["jugadores"] == []


def test_guardar_y_leer_plan(client, auth_admin, auth_entrenador, torneo_id, agregar_miembro):
    pid = _partido(client, auth_admin, torneo_id)
    por = agregar_miembro(auth_entrenador, 1, "Portero P", "portero@demo.com")
    del_ = agregar_miembro(auth_entrenador, 1, "Delantero D", "delantero@demo.com")

    cuerpo = {
        "equipo_id": 1, "formacion": "4-3-3",
        "jugadores": [
            {"jugador_equipo_id": por["je_id"], "posicion": "POR", "orden": 0},
            {"jugador_equipo_id": del_["je_id"], "posicion": "DEL", "orden": 9},
        ],
    }
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json=cuerpo)
    assert r.status_code == 200
    d = r.json()
    assert d["formacion"] == "4-3-3" and len(d["jugadores"]) == 2
    portero = next(j for j in d["jugadores"] if j["posicion"] == "POR")
    # snapshot del nombre (del usuario) y del jugador_id (para el árbitro)
    assert portero["nombre"] == "Portero P" and portero["jugador_id"] == por["jugador_id"]

    r2 = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_entrenador)
    assert r2.json()["formacion"] == "4-3-3" and len(r2.json()["jugadores"]) == 2


def test_jugador_de_otro_equipo_rechazado(client, auth_admin, auth_entrenador, torneo_id, agregar_miembro):
    pid = _partido(client, auth_admin, torneo_id)
    ajeno = agregar_miembro(auth_entrenador, 2, "Ajeno", "ajeno@demo.com")  # en equipo 2
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": ajeno["je_id"], "posicion": "POR", "orden": 0}]})
    assert r.status_code == 400


def test_jugador_repetido_rechazado(client, auth_admin, auth_entrenador, torneo_id, agregar_miembro):
    pid = _partido(client, auth_admin, torneo_id)
    m = agregar_miembro(auth_entrenador, 1, "Uno", "uno@demo.com")
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [
            {"jugador_equipo_id": m["je_id"], "posicion": "POR", "orden": 0},
            {"jugador_equipo_id": m["je_id"], "posicion": "DEF", "orden": 1},
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
    client.post(f"/partidos/{pid}/iniciar", headers=auth_admin)
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2", "jugadores": []})
    assert r.status_code == 409


def test_arbitro_puede_ver_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, agregar_miembro):
    # Partido con árbitro asignado
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2, "arbitro_id": arbitro_id,
    }).json()["id"]
    m = agregar_miembro(auth_entrenador, 1, "Titular", "titular@demo.com")
    client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": m["je_id"], "posicion": "POR", "orden": 0}]})
    # El árbitro asignado puede leer el plan del equipo local
    r = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_arbitro)
    assert r.status_code == 200 and len(r.json()["jugadores"]) == 1
    assert r.json()["jugadores"][0]["jugador_id"] == m["jugador_id"]


def test_mis_partidos_entrenador(client, auth_admin, auth_entrenador, torneo_id):
    _partido(client, auth_admin, torneo_id)
    r = client.get("/equipos/mis-partidos", headers=auth_entrenador)
    assert r.status_code == 200 and len(r.json()) >= 1
    assert r.json()[0]["mi_equipo_id"] in (1, 2) and "rival_nombre" in r.json()[0]


def test_no_guarda_plan_vacio(client, auth_admin, auth_entrenador, torneo_id, agregar_miembro):
    """
    La pantalla del entrenador (LineupScreen) permitía confirmar una alineación
    sin ningún jugador. El servidor la aceptaba y el partido quedaba sin plan.
    """
    pid = _partido(client, auth_admin, torneo_id)
    r = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador,
                   json={"equipo_id": 1, "formacion": "4-4-2", "jugadores": []})
    assert r.status_code == 400, r.text
    assert "jugador" in r.json()["detail"].lower()


def test_se_puede_reemplazar_un_plan_existente(client, auth_admin, auth_entrenador,
                                               torneo_id, agregar_miembro):
    """Rechazar el plan vacío no debe impedir corregir uno ya guardado."""
    pid = _partido(client, auth_admin, torneo_id)
    a = agregar_miembro(auth_entrenador, 1, "Uno", "uno@demo.com")
    b = agregar_miembro(auth_entrenador, 1, "Dos", "dos@demo.com")
    base = {"equipo_id": 1, "formacion": "4-4-2"}
    r1 = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador,
                    json={**base, "jugadores": [{"jugador_equipo_id": a["je_id"], "posicion": "POR", "orden": 0}]})
    assert r1.status_code == 200
    r2 = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador,
                    json={**base, "jugadores": [{"jugador_equipo_id": b["je_id"], "posicion": "DEL", "orden": 9}]})
    assert r2.status_code == 200 and len(r2.json()["jugadores"]) == 1
    assert r2.json()["jugadores"][0]["nombre"] == "Dos"
