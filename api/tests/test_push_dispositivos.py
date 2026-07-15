"""Pruebas del modelo DispositivoPush (registro de tokens de push)."""
from app import models


def test_dispositivo_push_roundtrip(db_session):
    db = db_session()
    # 'miembro@demo.com' se siembra en conftest; tomamos su id
    usuario = db.query(models.Usuario).filter_by(correo="miembro@demo.com").first()
    db.add(models.DispositivoPush(
        usuario_id=usuario.id, token="ExponentPushToken[abc123]", plataforma="android",
    ))
    db.commit()

    guardado = db.query(models.DispositivoPush).filter_by(usuario_id=usuario.id).one()
    assert guardado.token == "ExponentPushToken[abc123]"
    assert guardado.plataforma == "android"
    assert guardado in usuario.dispositivos_push
    db.close()
