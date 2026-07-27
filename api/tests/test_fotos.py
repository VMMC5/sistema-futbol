"""Fotos de perfil de usuario."""


def test_usuario_nace_sin_foto(client, auth_admin):
    # El superadmin ve la ficha de cualquier usuario; sin foto, tiene_foto=False.
    r = client.get("/usuarios/1", headers=auth_admin)
    assert r.status_code == 200
    assert r.json()["tiene_foto"] is False


import io


def _png_rojo(ancho=800, alto=400):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_normaliza_a_jpeg_cuadrado_512():
    from app import fotos_service
    from PIL import Image
    salida = fotos_service.normalizar_a_jpeg(_png_rojo())
    img = Image.open(io.BytesIO(salida))
    assert img.format == "JPEG"
    assert img.size == (512, 512)


def test_normaliza_rechaza_no_imagen():
    from app import fotos_service
    import pytest
    with pytest.raises(ValueError):
        fotos_service.normalizar_a_jpeg(b"esto no es una imagen")


def _subir(client, headers, datos=None, tipo="image/png", nombre="f.png"):
    datos = datos if datos is not None else _png_rojo()
    return client.post("/usuarios/me/foto", headers=headers,
                       files={"foto": (nombre, datos, tipo)})


def test_subir_foto_marca_tiene_foto(client, auth_entrenador):
    r = _subir(client, auth_entrenador)
    assert r.status_code == 200, r.text
    assert r.json()["tiene_foto"] is True


def test_servir_foto_devuelve_jpeg(client, auth_entrenador):
    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_servir_foto_sin_token_401(client, auth_entrenador):
    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto")  # sin headers
    assert r.status_code == 401


def test_servir_foto_de_usuario_sin_foto_404(client, auth_admin, auth_entrenador):
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    r = client.get(f"/usuarios/{yo['id']}/foto", headers=auth_admin)
    assert r.status_code == 404


def test_subir_no_imagen_400(client, auth_entrenador):
    r = _subir(client, auth_entrenador, datos=b"xxx", tipo="text/plain", nombre="x.txt")
    assert r.status_code == 400


def test_reemplazar_foto_borra_la_anterior(client, db_session, auth_entrenador):
    """Reemplazar la foto NO debe dejar el archivo anterior huérfano en disco.

    Se identifica el archivo por su nombre (guardado en foto_nombre), así la
    comprobación es exacta para ESTE usuario e inmune a las fotos que otros
    tests dejen en el directorio compartido FOTOS_DIR.
    """
    import os
    from app import models
    from app.routers import usuarios as u

    _subir(client, auth_entrenador)
    yo = client.get("/auth/me", headers=auth_entrenador).json()
    db = db_session()
    primera = db.get(models.Usuario, yo["id"]).foto_nombre
    db.close()
    assert primera and os.path.exists(os.path.join(u.FOTOS_DIR, primera))

    _subir(client, auth_entrenador)  # reemplazo
    db = db_session()
    segunda = db.get(models.Usuario, yo["id"]).foto_nombre
    db.close()
    assert segunda and segunda != primera
    # la anterior se borró (sin huérfanos); la nueva está en su lugar
    assert not os.path.exists(os.path.join(u.FOTOS_DIR, primera))
    assert os.path.exists(os.path.join(u.FOTOS_DIR, segunda))


def test_borrar_propia_foto(client, auth_entrenador):
    _subir(client, auth_entrenador)
    r = client.delete("/usuarios/me/foto", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.json()["tiene_foto"] is False


def test_borrar_foto_ajena_no_admin_403(client, auth_entrenador, auth_arbitro):
    _subir(client, auth_arbitro)
    arb = client.get("/auth/me", headers=auth_arbitro).json()
    r = client.delete(f"/usuarios/{arb['id']}/foto", headers=auth_entrenador)
    assert r.status_code == 403


def test_admin_borra_foto_ajena(client, auth_admin, auth_arbitro):
    _subir(client, auth_arbitro)
    arb = client.get("/auth/me", headers=auth_arbitro).json()
    r = client.delete(f"/usuarios/{arb['id']}/foto", headers=auth_admin)
    assert r.status_code == 200
