"""Pruebas del panel del árbitro: eventos enriquecidos, autogol, acta y horario."""
from datetime import datetime, timedelta


def _partido_en_juego(client, auth_admin, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2, "arbitro_id": arbitro_id,
    }).json()["id"]
    return pid


def test_no_iniciar_antes_de_hora(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    futuro = (datetime.now() + timedelta(days=1)).isoformat()
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id, "fecha_hora": futuro,
    }).json()["id"]
    r = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert r.status_code == 409  # aún no es la hora


def test_gol_con_asistencia_y_subtipo(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, agregar_miembro, auth_entrenador):
    a = agregar_miembro(auth_entrenador, 1, "Anotador", "anotador@demo.com")
    b = agregar_miembro(auth_entrenador, 1, "Asistente", "asistente@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)

    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": a["jugador_id"],
        "jugador_secundario_id": b["jugador_id"], "subtipo": "penal", "minuto": 23,
    })
    assert r.status_code == 201
    d = r.json()
    assert d["subtipo"] == "penal" and d["jugador_secundario_id"] == b["jugador_id"]
    p = client.get(f"/partidos/{pid}", headers=auth_arbitro).json()
    assert p["goles_local"] == 1 and p["goles_visitante"] == 0


def test_autogol_cuenta_para_el_rival(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    # Autogol del equipo local => suma al visitante
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "subtipo": "autogol", "minuto": 30})
    assert r.status_code == 201
    p = client.get(f"/partidos/{pid}", headers=auth_arbitro).json()
    assert p["goles_local"] == 0 and p["goles_visitante"] == 1
    # Borrarlo descuenta al visitante
    eid = r.json()["id"]
    client.delete(f"/partidos/{pid}/eventos/{eid}", headers=auth_arbitro)
    p = client.get(f"/partidos/{pid}", headers=auth_arbitro).json()
    assert p["goles_visitante"] == 0


def test_autogol_no_cuenta_para_goleo(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, agregar_miembro, auth_entrenador):
    m = agregar_miembro(auth_entrenador, 1, "Despistado", "despistado@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": m["jugador_id"], "subtipo": "autogol", "minuto": 10})
    gol = client.get("/estadisticas/goleadores", headers=auth_admin).json()
    assert all(g["jugador_id"] != m["jugador_id"] for g in gol)


def test_cambio_con_jugador_que_entra(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, agregar_miembro, auth_entrenador):
    sale = agregar_miembro(auth_entrenador, 1, "Sale", "sale@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra", "entra@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1,
        "jugador_id": sale["jugador_id"], "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    assert r.status_code == 201
    assert r.json()["jugador_secundario_id"] == entra["jugador_id"]


def test_firmar_acta(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    # No se puede firmar antes de finalizar
    assert client.post(f"/partidos/{pid}/acta", headers=auth_arbitro).status_code == 409
    client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/acta", headers=auth_arbitro)
    assert r.status_code == 200 and r.json()["acta_firmada"] is True


def test_plan_incluye_suplentes(client, auth_admin, auth_entrenador, torneo_id, agregar_miembro):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}).json()["id"]
    titular = agregar_miembro(auth_entrenador, 1, "Titular", "titu@demo.com")
    suplente = agregar_miembro(auth_entrenador, 1, "Banca", "banca@demo.com")
    client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": titular["je_id"], "posicion": "POR", "orden": 0}]})
    r = client.get(f"/partidos/{pid}/plan?equipo_id=1", headers=auth_entrenador).json()
    assert len(r["jugadores"]) == 1
    assert any(s["jugador_id"] == suplente["jugador_id"] for s in r["suplentes"])


def test_evento_sin_minuto_es_422(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1})
    assert r.status_code == 422


def test_evento_con_minuto_fuera_de_rango_es_422(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    for minuto in (-1, 131):
        r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
            "tipo": "gol", "equipo_id": 1, "minuto": minuto})
        assert r.status_code == 422


def _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, je_ids):
    """Partido con plan del equipo 1 y en juego. El plan se guarda ANTES de
    iniciar: después de iniciar, PUT /plan responde 409."""
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id}).json()["id"]
    r_plan = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": je, "posicion": "DEF", "orden": i}
                      for i, je in enumerate(je_ids)]})
    assert r_plan.status_code == 200, r_plan.text
    r_iniciar = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert r_iniciar.status_code == 200, r_iniciar.text
    return pid


def test_evento_sobre_expulsado_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                       torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Expulsado", "expulsado@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 40})
    assert r.status_code == 409
    assert "expulsado" in r.json()["detail"].lower()


def test_evento_sobre_jugador_que_ya_salio_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                  torneo_id, auth_entrenador, agregar_miembro):
    sale = agregar_miembro(auth_entrenador, 1, "Salio Ya", "salioya@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entro Ya", "entroya@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": sale["jugador_id"], "minuto": 70})
    assert r.status_code == 409


def test_evento_sobre_el_que_entro_de_cambio_se_acepta(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    sale = agregar_miembro(auth_entrenador, 1, "Sale Ok", "saleok@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra Ok", "entraok@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": entra["jugador_id"], "minuto": 70})
    assert r.status_code == 201


def test_cambio_con_el_que_sale_fuera_del_campo_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    titular = agregar_miembro(auth_entrenador, 1, "Titular Cbio", "titcbio@demo.com")
    banca_a = agregar_miembro(auth_entrenador, 1, "Banca A", "bancaa@demo.com")
    banca_b = agregar_miembro(auth_entrenador, 1, "Banca B", "bancab@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [titular["je_id"]])
    # banca_a no está en el campo: no puede "salir"
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": banca_a["jugador_id"],
        "jugador_secundario_id": banca_b["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_cambio_con_el_que_entra_ya_en_el_campo_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                                       torneo_id, auth_entrenador, agregar_miembro):
    uno = agregar_miembro(auth_entrenador, 1, "Titular Uno", "tituno@demo.com")
    dos = agregar_miembro(auth_entrenador, 1, "Titular Dos", "titdos@demo.com")
    pid = _plan_y_juego(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                        torneo_id, [uno["je_id"], dos["je_id"]])
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": uno["jugador_id"],
        "jugador_secundario_id": dos["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_cambio_sin_los_dos_jugadores_es_409(client, auth_admin, auth_arbitro, arbitro_id,
                                             torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Solo Uno", "solouno@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 55})
    assert r.status_code == 409


def test_evento_sin_jugador_sigue_siendo_valido(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    """El autogol atribuido solo al equipo no lleva jugador: no hay nada que validar."""
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "subtipo": "autogol", "minuto": 30})
    assert r.status_code == 201


def test_segunda_amarilla_genera_roja_automatica(client, auth_admin, auth_arbitro, arbitro_id,
                                                 torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Doble Amarilla", "doble@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 65})
    # El endpoint devuelve la amarilla, que es lo que se pidió crear
    assert r.status_code == 201 and r.json()["tipo"] == "tarjeta_amarilla"

    eventos = client.get(f"/partidos/{pid}/eventos", headers=auth_arbitro).json()
    rojas = [e for e in eventos
             if e["tipo"] == "tarjeta_roja" and e["jugador_id"] == m["jugador_id"]]
    assert len(rojas) == 1
    assert rojas[0]["minuto"] == 65
    assert "doble" in (rojas[0]["detalle"] or "").lower()


def test_una_sola_amarilla_no_genera_roja(client, auth_admin, auth_arbitro, arbitro_id,
                                          torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Una Amarilla", "unaamarilla@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 20})
    eventos = client.get(f"/partidos/{pid}/eventos", headers=auth_arbitro).json()
    assert not any(e["tipo"] == "tarjeta_roja" for e in eventos)


def test_tras_la_doble_amarilla_el_jugador_no_recibe_mas_eventos(
        client, auth_admin, auth_arbitro, arbitro_id, torneo_id, auth_entrenador, agregar_miembro):
    m = agregar_miembro(auth_entrenador, 1, "Fuera Ya", "fuueraya@demo.com")
    pid = _partido_en_juego(client, auth_admin, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    for minuto in (20, 65):
        client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
            "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": minuto})
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": m["jugador_id"], "minuto": 80})
    assert r.status_code == 409
