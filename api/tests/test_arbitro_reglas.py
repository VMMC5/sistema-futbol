"""Choque de horario del árbitro, disponibilidad y empate en eliminación."""


def _torneo(client, auth_admin, tipo="Liga"):
    return client.post("/torneos", headers=auth_admin,
                       json={"nombre": f"T {tipo}", "sede_id": 1, "tipo": tipo}).json()["id"]


def _partido(client, auth_admin, tid, **over):
    body = {"torneo_id": tid, "equipo_local_id": 1, "equipo_visitante_id": 2}
    body.update(over)
    return client.post("/partidos", headers=auth_admin, json=body)


def test_choque_de_horario_al_crear(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    r1 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    assert r1.status_code == 201, r1.text
    # mismo árbitro, misma fecha/hora -> 409
    r2 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    assert r2.status_code == 409
    # misma fecha, otra hora -> OK
    r3 = _partido(client, auth_admin, tid,
                  arbitro_id=arbitro_id, fecha_hora="2026-09-05T18:00:00Z")
    assert r3.status_code == 201, r3.text


def test_choque_de_horario_al_actualizar(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    _partido(client, auth_admin, tid,
             arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    libre = _partido(client, auth_admin, tid,
                     fecha_hora="2026-09-05T16:00:00Z").json()["id"]
    r = client.put(f"/partidos/{libre}", headers=auth_admin,
                   json={"arbitro_id": arbitro_id})
    assert r.status_code == 409
    # reasignarle al MISMO partido su propio árbitro no choca consigo mismo
    ocupado = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()[0]["id"]
    r = client.put(f"/partidos/{ocupado}", headers=auth_admin,
                   json={"arbitro_id": arbitro_id})
    assert r.status_code == 200, r.text


def test_arbitros_disponibles_filtra_ocupados(client, auth_admin, arbitro_id):
    tid = _torneo(client, auth_admin)
    _partido(client, auth_admin, tid,
             arbitro_id=arbitro_id, fecha_hora="2026-09-05T16:00:00Z")
    otro = _partido(client, auth_admin, tid,
                    fecha_hora="2026-09-05T16:00:00Z").json()["id"]
    disponibles = client.get(f"/partidos/{otro}/arbitros-disponibles",
                             headers=auth_admin).json()
    assert arbitro_id not in [a["id"] for a in disponibles]
    # sin fecha_hora no hay choque posible: aparece
    sin_fecha = _partido(client, auth_admin, tid).json()["id"]
    disponibles = client.get(f"/partidos/{sin_fecha}/arbitros-disponibles",
                             headers=auth_admin).json()
    assert arbitro_id in [a["id"] for a in disponibles]


def _en_juego_empatado(db_session, tid, arbitro_id, goles=(1, 1)):
    from app import models
    db = db_session()
    p = models.Partido(torneo_id=tid, equipo_local_id=1, equipo_visitante_id=2,
                       arbitro_id=arbitro_id, estado="en_juego",
                       goles_local=goles[0], goles_visitante=goles[1])
    db.add(p)
    db.commit()
    pid = p.id
    db.close()
    return pid


def test_eliminacion_no_finaliza_empatado(client, db_session, auth_admin,
                                          auth_arbitro, arbitro_id):
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    pid = _en_juego_empatado(db_session, tid, arbitro_id)
    r = client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    assert r.status_code == 409
    # con desempate sí finaliza
    pid2 = _en_juego_empatado(db_session, tid, arbitro_id, goles=(2, 1))
    r = client.post(f"/partidos/{pid2}/finalizar", headers=auth_arbitro)
    assert r.status_code == 200, r.text


def test_liga_si_puede_finalizar_empatada(client, db_session, auth_admin,
                                          auth_arbitro, arbitro_id):
    tid = _torneo(client, auth_admin, tipo="Liga")
    pid = _en_juego_empatado(db_session, tid, arbitro_id)
    r = client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    assert r.status_code == 200, r.text
