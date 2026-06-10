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
