"""Fotos de perfil de usuario."""


def test_usuario_nace_sin_foto(client, auth_admin):
    # El superadmin ve la ficha de cualquier usuario; sin foto, tiene_foto=False.
    r = client.get("/usuarios/1", headers=auth_admin)
    assert r.status_code == 200
    assert r.json()["tiene_foto"] is False
