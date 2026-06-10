"""Pruebas de invitaciones a equipo (lado del jugador)."""


def _jugador(client, nombre="Jug Uno", correo="jug1@demo.com"):
    client.post("/auth/register", json={"nombre": nombre, "correo": correo, "password": "clave12345"})
    tok = client.post("/auth/login", json={"correo": correo, "password": "clave12345"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    jid = client.get("/auth/me", headers=h).json()["id"]
    return jid, h


def test_jugador_ve_y_acepta_invitacion(client, auth_entrenador):
    jid, h = _jugador(client)
    inv = client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()

    # El jugador la ve como pendiente (su "notificación")
    mias = client.get("/invitaciones/mias", headers=h).json()
    assert any(i["id"] == inv["id"] and i["equipo_nombre"] for i in mias)

    # Acepta -> entra al equipo
    r = client.post(f"/invitaciones/{inv['id']}/aceptar", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"
    eq = client.get("/equipos/1", headers=auth_entrenador).json()
    assert any(j["jugador_id"] == jid for j in eq["jugadores"])
    # Ya no tiene invitaciones pendientes
    assert client.get("/invitaciones/mias", headers=h).json() == []


def test_aceptar_una_rechaza_las_demas(client, auth_entrenador):
    jid, h = _jugador(client, "Multi", "multi@demo.com")
    inv1 = client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()
    inv2 = client.post("/equipos/2/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()

    client.post(f"/invitaciones/{inv1['id']}/aceptar", headers=h)
    # La segunda quedó sin efecto (ya no pendiente)
    assert client.get("/invitaciones/mias", headers=h).json() == []
    # Y no puede aceptarla
    r = client.post(f"/invitaciones/{inv2['id']}/aceptar", headers=h)
    assert r.status_code == 409


def test_rechazar_invitacion(client, auth_entrenador):
    jid, h = _jugador(client, "Rechaza", "rechaza@demo.com")
    inv = client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()
    r = client.post(f"/invitaciones/{inv['id']}/rechazar", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "rechazada"
    # No entró al equipo
    eq = client.get("/equipos/1", headers=auth_entrenador).json()
    assert all(j["jugador_id"] != jid for j in eq["jugadores"])


def test_no_aceptar_invitacion_ajena(client, auth_entrenador):
    jid, h = _jugador(client, "Dueno", "dueno@demo.com")
    _, h_otro = _jugador(client, "Otro", "otro@demo.com")
    inv = client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()
    # Otro jugador no puede aceptar la invitación de alguien más
    assert client.post(f"/invitaciones/{inv['id']}/aceptar", headers=h_otro).status_code == 404
