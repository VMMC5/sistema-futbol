"""Pruebas del panel del jugador: estadísticas, próximos partidos, notificaciones,
perfil y disponibilidad de canchas."""


def _jugador(client, nombre="Juga Dor", correo="juga@demo.com"):
    client.post("/auth/register", json={"nombre": nombre, "correo": correo, "password": "clave12345"})
    tok = client.post("/auth/login", json={"correo": correo, "password": "clave12345"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    jid = client.get("/auth/me", headers=h).json()["id"]
    return jid, h


def test_estadisticas_jugador_sin_equipo(client):
    _, h = _jugador(client)
    r = client.get("/jugador/estadisticas", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["goles"] == 0 and d["partidos"] == 0 and d["torneos"] == []


def test_estadisticas_con_eventos(client, auth_admin, auth_arbitro, arbitro_id, torneo_id, auth_entrenador, agregar_miembro):
    info = agregar_miembro(auth_entrenador, 1, "Goleador", "goleador@demo.com")
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2, "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "gol", "equipo_id": 1, "jugador_id": info["jugador_id"], "subtipo": "normal", "minuto": 10})
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": info["jugador_id"], "minuto": 20})
    client.post(f"/partidos/{pid}/finalizar", headers=auth_arbitro)

    r = client.get("/jugador/estadisticas", headers=info["headers"]).json()
    assert r["goles"] == 1 and r["amarillas"] == 1 and r["partidos"] == 1
    assert r["minutos_estimados"] == 90 and len(r["por_jornada"]) == 1
    assert any(t["id"] == torneo_id for t in r["torneos"])
    # Filtro por torneo inexistente => sin goles
    r2 = client.get("/jugador/estadisticas?torneo_id=99999", headers=info["headers"]).json()
    assert r2["goles"] == 0


def test_proximos_partidos_jugador(client, auth_admin, torneo_id, auth_entrenador, agregar_miembro):
    info = agregar_miembro(auth_entrenador, 1, "Citado", "citado@demo.com")
    client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2})
    r = client.get("/jugador/proximos-partidos", headers=info["headers"])
    assert r.status_code == 200 and len(r.json()) >= 1
    assert "rival" in r.json()[0]


def test_notificaciones(client, auth_entrenador):
    jid, h = _jugador(client, "Notif", "notif@demo.com")
    # Una invitación genera notificación
    client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid})
    lista = client.get("/notificaciones", headers=h).json()
    assert len(lista) >= 1
    nid = lista[0]["id"]
    # Marcar leídas
    assert client.post("/notificaciones/marcar-leidas", headers=h).status_code == 200
    assert all(n["leida"] for n in client.get("/notificaciones", headers=h).json())
    # Eliminar
    assert client.delete(f"/notificaciones/{nid}", headers=h).status_code == 204
    assert all(n["id"] != nid for n in client.get("/notificaciones", headers=h).json())


def test_no_elimina_notificacion_ajena(client, auth_entrenador):
    jid, h = _jugador(client, "Duenio", "duenion@demo.com")
    _, h_otro = _jugador(client, "Intruso", "intruso@demo.com")
    client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid})
    nid = client.get("/notificaciones", headers=h).json()[0]["id"]
    assert client.delete(f"/notificaciones/{nid}", headers=h_otro).status_code == 404


def test_editar_perfil(client):
    _, h = _jugador(client, "Antes", "perfil@demo.com")
    r = client.put("/auth/me", headers=h, json={"nombre": "Después", "telefono": "7711234567"})
    assert r.status_code == 200
    assert r.json()["nombre"] == "Después" and r.json()["telefono"] == "7711234567"
    assert client.get("/auth/me", headers=h).json()["nombre"] == "Después"


def test_disponibilidad_canchas(client, auth_admin):
    _, h = _jugador(client, "Reserva", "reserva@demo.com")
    # crea sede + cancha
    sede = client.post("/sedes", headers=auth_admin, json={"nombre": "Sede Test"}).json()["id"]
    cancha = client.post("/canchas", headers=auth_admin, json={"sede_id": sede, "nombre": "C1"}).json()["id"]
    # reserva un horario
    client.post("/reservas", headers=h, json={
        "cancha_id": cancha, "fecha": "2030-01-01", "hora_inicio": "18:00", "hora_fin": "19:00"})
    r = client.get(f"/canchas/{cancha}/disponibilidad?fecha=2030-01-01", headers=h)
    assert r.status_code == 200 and "18:00" in r.json()["ocupados"]


def test_buscar_sede(client, auth_admin):
    _, h = _jugador(client, "Busca", "busca@demo.com")
    client.post("/sedes", headers=auth_admin, json={"nombre": "Polideportivo Norte"})
    r = client.get("/sedes?buscar=norte", headers=h)
    assert r.status_code == 200 and all("norte" in s["nombre"].lower() for s in r.json())
