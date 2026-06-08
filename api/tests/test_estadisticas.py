"""
Pruebas de estadísticas.

Se juega un partido completo (Equipo A 2 - 1 Equipo B) con tarjetas, y se
verifica que goleadores, tarjetas y tabla de posiciones se calculen bien.
"""


def _jugar_partido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, eventos):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    for ev in eventos:
        client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json=ev)
    client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    return pid


def _eventos_2_1(miembro_id):
    # Equipo A (local) 2 - 1 Equipo B (visitante); miembro mete los 2 goles locales
    return [
        {"tipo": "gol", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 10},
        {"tipo": "gol", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 20},
        {"tipo": "gol", "equipo_id": 2, "minuto": 30},
        {"tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 40},
        {"tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 50},
    ]


def test_goleadores(client, auth_admin, auth_arbitro, arbitro_id, miembro_id, torneo_id):
    _jugar_partido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, _eventos_2_1(miembro_id))

    r = client.get(f"/estadisticas/goleadores?torneo_id={torneo_id}", headers=auth_admin)
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1                      # solo el miembro tiene goles con jugador
    assert datos[0]["jugador_id"] == miembro_id
    assert datos[0]["goles"] == 2


def test_tarjetas(client, auth_admin, auth_arbitro, arbitro_id, miembro_id, torneo_id):
    _jugar_partido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, _eventos_2_1(miembro_id))

    r = client.get(f"/estadisticas/tarjetas?torneo_id={torneo_id}", headers=auth_admin)
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1
    assert datos[0]["jugador_id"] == miembro_id
    assert datos[0]["amarillas"] == 1 and datos[0]["rojas"] == 1


def test_tabla_de_posiciones(client, auth_admin, auth_arbitro, arbitro_id, miembro_id, torneo_id):
    _jugar_partido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, _eventos_2_1(miembro_id))

    r = client.get(f"/estadisticas/torneos/{torneo_id}/tabla", headers=auth_admin)
    assert r.status_code == 200
    tabla = r.json()
    assert len(tabla) == 2

    # El Equipo A (id=1) ganó 2-1 -> primero, 3 puntos
    primero = tabla[0]
    assert primero["equipo_id"] == 1
    assert primero["puntos"] == 3 and primero["pg"] == 1 and primero["pj"] == 1
    assert primero["gf"] == 2 and primero["gc"] == 1 and primero["dg"] == 1

    # El Equipo B (id=2) perdió -> segundo, 0 puntos
    segundo = tabla[1]
    assert segundo["equipo_id"] == 2
    assert segundo["puntos"] == 0 and segundo["pp"] == 1
    assert segundo["gf"] == 1 and segundo["gc"] == 2 and segundo["dg"] == -1


def test_empate_reparte_puntos(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    # 1-1: un punto para cada uno
    eventos = [
        {"tipo": "gol", "equipo_id": 1, "minuto": 10},
        {"tipo": "gol", "equipo_id": 2, "minuto": 70},
    ]
    _jugar_partido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, eventos)

    tabla = client.get(f"/estadisticas/torneos/{torneo_id}/tabla", headers=auth_admin).json()
    assert all(fila["puntos"] == 1 and fila["pe"] == 1 for fila in tabla)


def test_partido_no_finalizado_no_cuenta(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    # Partido creado e iniciado pero NO finalizado: los equipos salen con 0 PJ
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2, "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1})

    tabla = client.get(f"/estadisticas/torneos/{torneo_id}/tabla", headers=auth_admin).json()
    assert all(fila["pj"] == 0 and fila["puntos"] == 0 for fila in tabla)


def test_tabla_torneo_inexistente(client, auth_admin):
    assert client.get("/estadisticas/torneos/999/tabla", headers=auth_admin).status_code == 404


def test_estadisticas_requieren_token(client):
    assert client.get("/estadisticas/goleadores").status_code == 401
