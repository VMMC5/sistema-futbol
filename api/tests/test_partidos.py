"""
Pruebas de partidos y eventos en vivo.

Datos sembrados disponibles (ver conftest):
- equipos id=1 (A) e id=2 (B), una cancha id=1
- usuario arbitro (fixture auth_arbitro / arbitro_id) y admin (auth_admin)
- el torneo se crea con el fixture torneo_id
"""


def _crear_partido(client, auth_admin, torneo_id, arbitro_id=None):
    cuerpo = {"torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2}
    if arbitro_id:
        cuerpo["arbitro_id"] = arbitro_id
    return client.post("/partidos", headers=auth_admin, json=cuerpo)


# ---------- Creacion (admin) ----------
def test_admin_crea_partido(client, auth_admin, torneo_id):
    r = _crear_partido(client, auth_admin, torneo_id)
    assert r.status_code == 201
    assert r.json()["estado"] == "programado"
    assert r.json()["goles_local"] == 0


def test_equipos_iguales_rechazado(client, auth_admin, torneo_id):
    r = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 1,
    })
    assert r.status_code == 422


def test_jugador_no_crea_partido(client, auth_admin, torneo_id):
    client.post("/auth/register", json={"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"}).json()["access_token"]
    r = client.post("/partidos", headers={"Authorization": f"Bearer {tok}"}, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
    })
    assert r.status_code == 403


# ---------- Flujo del arbitro ----------
def test_arbitro_inicia_finaliza(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]

    r = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert r.status_code == 200 and r.json()["estado"] == "en_juego"

    r = client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)
    assert r.status_code == 200 and r.json()["estado"] == "finalizado"


def test_no_se_inicia_dos_veces(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro).status_code == 409


def test_arbitro_no_asignado_no_gestiona(client, auth_admin, auth_arbitro, torneo_id):
    # Partido SIN arbitro asignado: el arbitro de prueba no debe poder iniciarlo
    pid = _crear_partido(client, auth_admin, torneo_id).json()["id"]
    assert client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro).status_code == 403
    assert client.post(f"/partidos/{pid}/iniciar", headers=auth_admin).status_code == 200


# ---------- Eventos y marcador ----------
def test_gol_actualiza_marcador(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)

    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 12})
    assert r.status_code == 201
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 2, "minuto": 30})
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 55})

    partido = client.get(f"/partidos/{pid}", headers=auth_admin).json()
    assert partido["goles_local"] == 2 and partido["goles_visitante"] == 1


def test_evento_solo_en_juego(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1})
    assert r.status_code == 409


def test_evento_equipo_no_participa(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    r = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 99})
    assert r.status_code == 400


def test_borrar_gol_descuenta_marcador(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    eid = client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1}).json()["id"]

    assert client.get(f"/partidos/{pid}", headers=auth_admin).json()["goles_local"] == 1
    assert client.delete(f"/partidos/{pid}/eventos/{eid}", headers=auth_arbitro).status_code == 204
    assert client.get(f"/partidos/{pid}", headers=auth_admin).json()["goles_local"] == 0


def test_listar_eventos_ordenados(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = _crear_partido(client, auth_admin, torneo_id, arbitro_id).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "gol", "equipo_id": 1, "minuto": 40})
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={"tipo": "tarjeta_amarilla", "equipo_id": 2, "minuto": 10})

    eventos = client.get(f"/partidos/{pid}/eventos", headers=auth_admin).json()
    assert [e["minuto"] for e in eventos] == [10, 40]
