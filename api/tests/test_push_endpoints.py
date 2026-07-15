"""Pruebas de los endpoints de registro de dispositivos push."""


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_registrar_dispositivo(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    r = client.post("/notificaciones/dispositivos",
                    headers=h, json={"token": "ExponentPushToken[xyz]", "plataforma": "android"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_registrar_dispositivo_requiere_auth(client):
    r = client.post("/notificaciones/dispositivos", json={"token": "ExponentPushToken[xyz]"})
    assert r.status_code == 401


def test_registrar_token_repetido_es_idempotente(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    body = {"token": "ExponentPushToken[dup]", "plataforma": "ios"}
    assert client.post("/notificaciones/dispositivos", headers=h, json=body).status_code == 200
    # Segundo registro del mismo token: no duplica ni falla
    assert client.post("/notificaciones/dispositivos", headers=h, json=body).status_code == 200


def test_reasignar_token_a_otro_usuario(client):
    body = {"token": "ExponentPushToken[compartido]", "plataforma": "android"}
    h1 = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h1, json=body)
    # El mismo dispositivo ahora lo usa el entrenador
    h2 = _login(client, "entrenador@demo.com", "entrenadorpass123")
    r = client.post("/notificaciones/dispositivos", headers=h2, json=body)
    assert r.status_code == 200


def test_eliminar_dispositivo(client):
    h = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h,
                json={"token": "ExponentPushToken[borrar]"})
    r = client.request("DELETE", "/notificaciones/dispositivos",
                       headers=h, params={"token": "ExponentPushToken[borrar]"})
    assert r.status_code == 204
