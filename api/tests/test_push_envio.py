"""Pruebas del envío push (Expo mockeado) y del helper central."""
import pytest

from app import models, notificaciones_service as ns


@pytest.fixture
def usuario_con_token(db_session, monkeypatch):
    """Registra un dispositivo para 'miembro' y apunta SessionLocal a la BD de prueba."""
    # La tarea enviar_push abre su propia SessionLocal: en tests debe ser la de memoria.
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    db = db_session()
    usuario = db.query(models.Usuario).filter_by(correo="miembro@demo.com").first()
    db.add(models.DispositivoPush(usuario_id=usuario.id, token="ExponentPushToken[ok]", plataforma="ios"))
    db.commit()
    uid = usuario.id
    db.close()
    return uid


def test_enviar_push_llama_expo_con_el_token(usuario_con_token, monkeypatch):
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: (capturado.setdefault("m", mensajes), [])[1])

    ns.enviar_push(usuario_con_token, "Título", "Cuerpo")

    assert capturado["m"] == [
        {"to": "ExponentPushToken[ok]", "title": "Título", "body": "Cuerpo", "sound": "default"}
    ]


def test_enviar_push_purga_token_no_registrado(usuario_con_token, db_session, monkeypatch):
    # Expo responde que ese token ya no está registrado -> se debe borrar.
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: [
        {"status": "error", "message": "not registered",
         "details": {"error": "DeviceNotRegistered"}}
    ])

    ns.enviar_push(usuario_con_token, "T", "C")

    db = db_session()
    assert db.query(models.DispositivoPush).filter_by(usuario_id=usuario_con_token).count() == 0
    db.close()


def test_enviar_push_falla_no_lanza(usuario_con_token, monkeypatch):
    def explota(mensajes):
        raise RuntimeError("Expo caído")
    monkeypatch.setattr(ns, "_post_expo", explota)

    # No debe lanzar: best-effort.
    ns.enviar_push(usuario_con_token, "T", "C")


def test_enviar_push_sin_dispositivos_no_llama_expo(db_session, monkeypatch):
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    llamado = {"n": 0}
    monkeypatch.setattr(ns, "_post_expo", lambda mensajes: llamado.update(n=llamado["n"] + 1) or [])
    db = db_session()
    admin = db.query(models.Usuario).filter_by(correo="admin@demo.com").first()
    aid = admin.id
    db.close()

    ns.enviar_push(aid, "T", "C")

    assert llamado["n"] == 0
