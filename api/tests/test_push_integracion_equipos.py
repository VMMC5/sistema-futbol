"""La invitación a equipo debe encolar un push al jugador invitado."""
from app import models, notificaciones_service as ns


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_invitacion_encola_push(client, db_session, monkeypatch):
    # La tarea usa su propia SessionLocal: apuntarla a la BD de prueba.
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda m: (capturado.setdefault("m", m), [])[1])

    # 'miembro' ya está en Equipo A; usamos un jugador nuevo sin equipo.
    client.post("/auth/register", json={"nombre": "Libre", "correo": "libre@demo.com", "password": "clave12345"})
    h_jug = _login(client, "libre@demo.com", "clave12345")
    client.post("/notificaciones/dispositivos", headers=h_jug,
                json={"token": "ExponentPushToken[libre]", "plataforma": "android"})
    jid = client.get("/auth/me", headers=h_jug).json()["id"]

    # El entrenador (dueño del Equipo A, id=1) lo invita.
    h_ent = _login(client, "entrenador@demo.com", "entrenadorpass123")
    r = client.post("/equipos/1/invitaciones", headers=h_ent, json={"jugador_id": jid})
    assert r.status_code == 201

    # Se generó el push al token del jugador invitado.
    assert capturado["m"][0]["to"] == "ExponentPushToken[libre]"
    assert capturado["m"][0]["title"] == "Invitación a equipo"
    # Y la notificación quedó en BD (respaldo).
    db = db_session()
    assert db.query(models.Notificacion).filter_by(usuario_id=jid).count() == 1
    db.close()
