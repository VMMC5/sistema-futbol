"""Agregación de eventos por jugador (goles, asistencias, tarjetas, cambios)."""


def _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def test_resumen_gol_con_asistencia(client, db_session, auth_admin, auth_arbitro,
                                    arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    # gol de 'miembro' (id=miembro_id) asistido por otro; se registra vía API
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "normal", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 10,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res[miembro_id]["goles"] == 1


def test_resumen_autogol_no_suma_al_goleador(client, db_session, auth_admin,
                                             auth_arbitro, arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "autogol", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 20,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res.get(miembro_id, {}).get("goles", 0) == 0


def test_resumen_amarilla(client, db_session, auth_admin, auth_arbitro,
                          arbitro_id, torneo_id, miembro_id):
    from app import eventos_resumen
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 30,
    })
    db = db_session()
    res = eventos_resumen.resumen_por_jugador(db, pid)
    db.close()
    assert res[miembro_id]["amarillas"] == 1


def test_endpoint_resumen_jugadores(client, auth_admin, auth_arbitro,
                                    arbitro_id, torneo_id, miembro_id):
    pid = _partido_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "subtipo": "normal", "equipo_id": 1,
        "jugador_id": miembro_id, "minuto": 10,
    })
    r = client.get(f"/partidos/{pid}/resumen-jugadores", headers=auth_admin)
    assert r.status_code == 200
    assert r.json()[str(miembro_id)]["goles"] == 1
