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


def test_cambiar_fecha_avisa_a_arbitro_y_entrenador(client, auth_admin, auth_arbitro,
                                                    auth_entrenador, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes_arb = len(_notis(client, auth_arbitro))
    antes_ent = len(_notis(client, auth_entrenador))
    r = client.put(f"/partidos/{pid}", headers=auth_admin, json={"fecha_hora": "2027-01-15T18:00:00"})
    assert r.status_code == 200
    notis_arb = _notis(client, auth_arbitro)
    assert len(notis_arb) == antes_arb + 1 and notis_arb[0]["titulo"] == "Partido reprogramado"
    assert len(_notis(client, auth_entrenador)) == antes_ent + 1


def test_asignar_arbitro_despues_lo_avisa(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id).json()["id"]  # sin árbitro
    antes = len(_notis(client, auth_arbitro))
    client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": arbitro_id})
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1 and notis[0]["titulo"] == "Partido asignado"


def test_quitar_al_arbitro_lo_avisa(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes = len(_notis(client, auth_arbitro))
    r = client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": None})
    assert r.status_code == 200
    notis = _notis(client, auth_arbitro)
    assert len(notis) == antes + 1 and notis[0]["titulo"] == "Cambio de designación"


def test_actualizar_sin_cambios_relevantes_no_avisa(client, auth_admin, auth_arbitro,
                                                    arbitro_id, torneo_id):
    """Repetir el mismo árbitro no es un cambio: nadie recibe nada."""
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes = len(_notis(client, auth_arbitro))
    client.put(f"/partidos/{pid}", headers=auth_admin, json={"arbitro_id": arbitro_id})
    assert len(_notis(client, auth_arbitro)) == antes


def test_eliminar_partido_avisa(client, auth_admin, auth_arbitro, auth_entrenador,
                                arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    antes_arb = len(_notis(client, auth_arbitro))
    antes_ent = len(_notis(client, auth_entrenador))
    assert client.delete(f"/partidos/{pid}", headers=auth_admin).status_code == 204
    notis_arb = _notis(client, auth_arbitro)
    assert len(notis_arb) == antes_arb + 1 and notis_arb[0]["titulo"] == "Partido cancelado"
    assert len(_notis(client, auth_entrenador)) == antes_ent + 1


def test_torneo_nuevo_avisa_a_los_entrenadores(client, auth_admin, auth_entrenador):
    antes = len(_notis(client, auth_entrenador))
    r = client.post("/torneos", headers=auth_admin, json={"nombre": "Copa Avisos", "sede_id": 1})
    assert r.status_code == 201
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Torneo nuevo"
    assert "Copa Avisos" in notis[0]["mensaje"]


def test_torneo_nuevo_no_avisa_a_jugadores(client, auth_admin):
    tok = client.post("/auth/login", json={"correo": "miembro@demo.com", "password": "miembropass123"}).json()["access_token"]
    auth_miembro = {"Authorization": f"Bearer {tok}"}
    antes = len(_notis(client, auth_miembro))
    client.post("/torneos", headers=auth_admin, json={"nombre": "Copa Silencio", "sede_id": 1})
    assert len(_notis(client, auth_miembro)) == antes


def _torneo(client, auth_admin, **over):
    body = {"nombre": "Copa Inscripción", "sede_id": 1}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def test_inscripcion_gratis_avisa_aceptada(client, auth_admin, auth_entrenador):
    tid = _torneo(client, auth_admin)  # sin cuota -> aceptada directa
    antes = len(_notis(client, auth_entrenador))
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 201 and r.json()["estado"] == "aceptada"
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Inscripción aceptada"


def test_pago_de_otro_avisa_al_entrenador(client, auth_admin, auth_entrenador):
    """El admin paga la cuota en nombre del equipo: el entrenador (que no fue
    el pagador) recibe el aviso de aceptación."""
    tid = _torneo(client, auth_admin, cuota_inscripcion=500)
    iid = client.post("/inscripciones", headers=auth_entrenador,
                      json={"torneo_id": tid, "equipo_id": 1}).json()["id"]
    antes = len(_notis(client, auth_entrenador))
    r = client.post(f"/pagos/inscripcion/{iid}", headers=auth_admin, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
                    "cvv": "123", "titular": "Admin Demo"}})
    assert r.status_code == 201, r.text
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Inscripción aceptada"


def test_pago_propio_no_duplica_el_aviso(client, auth_admin, auth_entrenador):
    """El entrenador paga su propia cuota: recibe 'Pago confirmado' (existente)
    y NADA más — un solo aviso nuevo, no dos."""
    tid = _torneo(client, auth_admin, cuota_inscripcion=500)
    iid = client.post("/inscripciones", headers=auth_entrenador,
                      json={"torneo_id": tid, "equipo_id": 1}).json()["id"]
    antes = len(_notis(client, auth_entrenador))
    client.post(f"/pagos/inscripcion/{iid}", headers=auth_entrenador, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111234", "exp_mes": 12, "exp_anio": 2999,
                    "cvv": "123", "titular": "Entrenador Demo"}})
    notis = _notis(client, auth_entrenador)
    assert len(notis) == antes + 1
    assert notis[0]["titulo"] == "Pago confirmado"
