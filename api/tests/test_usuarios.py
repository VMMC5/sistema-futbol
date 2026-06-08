"""Pruebas de la gestión de usuarios (solo admin)."""


def _jugador(client):
    client.post("/auth/register", json={"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_listar_usuarios_solo_admin(client, auth_admin):
    r = client.get("/usuarios", headers=auth_admin)
    assert r.status_code == 200
    # conftest siembra admin, arbitro, entrenador y miembro
    assert len(r.json()) >= 4


def test_jugador_no_lista_usuarios(client):
    assert client.get("/usuarios", headers=_jugador(client)).status_code == 403


def test_listar_roles(client, auth_admin):
    r = client.get("/usuarios/roles", headers=auth_admin)
    assert r.status_code == 200
    assert set(["jugador", "entrenador", "arbitro", "superadmin"]).issubset(set(r.json()))


def test_admin_crea_usuario_y_puede_loguear(client, auth_admin):
    r = client.post("/usuarios", headers=auth_admin, json={
        "nombre": "Nuevo Arbitro", "correo": "nuevo@demo.com",
        "password": "arbitro12345", "rol": "arbitro",
    })
    assert r.status_code == 201 and r.json()["rol"] == "arbitro"
    # El usuario creado puede iniciar sesión (contraseña hasheada correctamente)
    assert client.post("/auth/login", json={"correo": "nuevo@demo.com", "password": "arbitro12345"}).status_code == 200


def test_correo_duplicado(client, auth_admin):
    datos = {"nombre": "Duplicado", "correo": "dup@demo.com", "password": "claveSegura123", "rol": "jugador"}
    client.post("/usuarios", headers=auth_admin, json=datos)
    assert client.post("/usuarios", headers=auth_admin, json=datos).status_code == 400


def test_rol_invalido(client, auth_admin):
    r = client.post("/usuarios", headers=auth_admin, json={
        "nombre": "Prueba", "correo": "y@demo.com", "password": "claveSegura123", "rol": "presidente",
    })
    assert r.status_code == 400


def test_admin_cambia_rol(client, auth_admin):
    uid = client.post("/usuarios", headers=auth_admin, json={
        "nombre": "Cambia", "correo": "cambia@demo.com", "password": "claveSegura123", "rol": "jugador",
    }).json()["id"]
    r = client.put(f"/usuarios/{uid}", headers=auth_admin, json={"rol": "entrenador"})
    assert r.status_code == 200 and r.json()["rol"] == "entrenador"


def test_desactivar_impide_login(client, auth_admin):
    uid = client.post("/usuarios", headers=auth_admin, json={
        "nombre": "Baja", "correo": "baja@demo.com", "password": "claveSegura123", "rol": "jugador",
    }).json()["id"]
    # Antes de desactivar, puede entrar
    assert client.post("/auth/login", json={"correo": "baja@demo.com", "password": "claveSegura123"}).status_code == 200
    # Se desactiva
    assert client.put(f"/usuarios/{uid}", headers=auth_admin, json={"activo": False}).status_code == 200
    # Ya no puede entrar
    assert client.post("/auth/login", json={"correo": "baja@demo.com", "password": "claveSegura123"}).status_code == 403


def test_admin_no_se_desactiva_a_si_mismo(client, auth_admin):
    yo = client.get("/auth/me", headers=auth_admin).json()["id"]
    assert client.put(f"/usuarios/{yo}", headers=auth_admin, json={"activo": False}).status_code == 400


def test_reset_password(client, auth_admin):
    uid = client.post("/usuarios", headers=auth_admin, json={
        "nombre": "Reset", "correo": "reset@demo.com", "password": "claveSegura123", "rol": "jugador",
    }).json()["id"]
    client.put(f"/usuarios/{uid}", headers=auth_admin, json={"password": "nuevaClave456"})
    assert client.post("/auth/login", json={"correo": "reset@demo.com", "password": "nuevaClave456"}).status_code == 200
