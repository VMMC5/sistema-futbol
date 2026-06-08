"""
Pruebas del módulo de autenticación y del CRUD de torneos.

Plantilla a copiar para los próximos módulos (reservas, equipos, partidos):
verifican tanto el "camino feliz" como el control de acceso por rol.

Ejecutar (dentro del contenedor):
    docker compose exec api pytest -v
"""


def _registrar_y_loguear_jugador(client):
    client.post("/auth/register", json={
        "nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123",
    })
    r = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------- Autenticación ----------
def test_registro_crea_jugador(client):
    r = client.post("/auth/register", json={
        "nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123",
    })
    assert r.status_code == 201
    assert r.json()["rol"] == "jugador"


def test_registro_correo_duplicado(client):
    datos = {"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"}
    client.post("/auth/register", json=datos)
    r = client.post("/auth/register", json=datos)
    assert r.status_code == 400


def test_login_contrasena_incorrecta(client):
    r = client.post("/auth/login", json={"correo": "admin@demo.com", "password": "mala"})
    assert r.status_code == 401


def test_me_requiere_token(client):
    assert client.get("/auth/me").status_code == 401


# ---------- CRUD de torneos + roles ----------
def test_listar_sin_token_no_autorizado(client):
    assert client.get("/torneos").status_code == 401


def test_jugador_no_puede_crear_torneo(client):
    auth = _registrar_y_loguear_jugador(client)
    r = client.post("/torneos", headers=auth, json={"nombre": "Copa X", "sede_id": 1})
    assert r.status_code == 403


def test_admin_crea_y_lista_torneo(client, auth_admin):
    r = client.post("/torneos", headers=auth_admin, json={
        "nombre": "Copa Verano", "sede_id": 1, "cupo_maximo": 8,
    })
    assert r.status_code == 201
    assert r.json()["estado"] == "programado"

    r = client.get("/torneos", headers=auth_admin)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_crear_con_sede_inexistente_falla(client, auth_admin):
    r = client.post("/torneos", headers=auth_admin, json={"nombre": "Copa", "sede_id": 999})
    assert r.status_code == 400


def test_actualizar_y_eliminar_torneo(client, auth_admin):
    tid = client.post("/torneos", headers=auth_admin, json={
        "nombre": "Copa", "sede_id": 1,
    }).json()["id"]

    r = client.put(f"/torneos/{tid}", headers=auth_admin, json={"estado": "en_curso"})
    assert r.status_code == 200 and r.json()["estado"] == "en_curso"

    assert client.delete(f"/torneos/{tid}", headers=auth_admin).status_code == 204
    assert len(client.get("/torneos", headers=auth_admin).json()) == 0


def test_fecha_fin_anterior_a_inicio_falla(client, auth_admin):
    r = client.post("/torneos", headers=auth_admin, json={
        "nombre": "Copa", "sede_id": 1,
        "fecha_inicio": "2026-06-10T10:00:00", "fecha_fin": "2026-06-01T10:00:00",
    })
    assert r.status_code == 422  # rechazado por validación del esquema
