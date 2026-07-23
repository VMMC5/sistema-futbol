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
