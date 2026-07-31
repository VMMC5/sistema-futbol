"""Avisos de negocio para árbitro y entrenador (partidos, torneos, inscripciones).

Todos los conteos son DELTAS antes/después: los fixtures ya generan avisos
propios (p. ej. el torneo del fixture avisará a los entrenadores).
"""


def _notis(client, auth):
    return client.get("/notificaciones", headers=auth).json()


def _crear_partido(client, auth_admin, torneo_id, arbitro_id=None, **over):
    body = {"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}
    if arbitro_id:
        body["arbitro_id"] = arbitro_id
    body.update(over)
    return client.post("/partidos", headers=auth_admin, json=body)


def test_crear_partido_avisa_al_arbitro(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    antes = len(_notis(client, auth_arbitro))
    r = _crear_partido(client, auth_admin, torneo_id, arbitro_id)
    assert r.status_code == 201
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Partido asignado"


def test_crear_partido_sin_arbitro_no_lo_avisa(client, auth_admin, auth_arbitro, torneo_id):
    antes = len(_notis(client, auth_arbitro))
    assert _crear_partido(client, auth_admin, torneo_id).status_code == 201
    assert len(_notis(client, auth_arbitro)) == antes


def test_crear_partido_avisa_una_vez_al_entrenador_de_ambos_equipos(
        client, auth_admin, auth_entrenador, arbitro_id, torneo_id):
    """Los equipos 1 y 2 son del MISMO entrenador: un aviso, no dos."""
    antes = len(_notis(client, auth_entrenador))
    _crear_partido(client, auth_admin, torneo_id, arbitro_id)
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Partido programado"
