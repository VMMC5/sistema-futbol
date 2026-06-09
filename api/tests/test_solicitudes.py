"""
Pruebas del flujo de solicitudes (entrenador/árbitro), contraseña temporal,
cambio de contraseña forzado y el endpoint público de inicio.
"""

PDF = ("credencial.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")


def _crear_solicitud(client, correo="coach@demo.com", rol="entrenador"):
    return client.post(
        "/solicitudes",
        data={"nombre": "Carlos Coach", "correo": correo, "telefono": "771", "rol_solicitado": rol},
        files={"documento": PDF},
    )


def test_crear_solicitud_publica(client):
    r = _crear_solicitud(client)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente" and r.json()["rol_solicitado"] == "entrenador"


def test_solicitud_rol_invalido(client):
    r = _crear_solicitud(client, correo="x@demo.com", rol="jugador")
    assert r.status_code == 400


def test_solicitud_correo_ya_registrado(client):
    # admin@demo.com ya existe (seed de conftest)
    r = _crear_solicitud(client, correo="admin@demo.com")
    assert r.status_code == 400


def test_documento_tipo_invalido(client):
    r = client.post(
        "/solicitudes",
        data={"nombre": "Carlos", "correo": "y@demo.com", "rol_solicitado": "arbitro"},
        files={"documento": ("malo.txt", b"texto", "text/plain")},
    )
    assert r.status_code == 400


def test_listar_solicitudes_solo_admin(client):
    _crear_solicitud(client)
    # sin token
    assert client.get("/solicitudes").status_code == 401


def test_flujo_completo_aceptar_y_cambio_forzado(client, auth_admin, monkeypatch):
    # Contraseña temporal predecible para poder iniciar sesión en la prueba
    import app.routers.solicitudes as mod
    monkeypatch.setattr(mod.secrets, "token_urlsafe", lambda n=9: "TempPass123")

    sid = _crear_solicitud(client, correo="nuevo.coach@demo.com").json()["id"]

    # El admin la ve en la lista de pendientes
    pendientes = client.get("/solicitudes", headers=auth_admin).json()
    assert any(s["id"] == sid for s in pendientes)

    # Aceptar -> crea el usuario
    r = client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin)
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"

    # El usuario puede iniciar sesión con la contraseña temporal,
    # y el login indica que debe cambiarla
    login = client.post("/auth/login", json={"correo": "nuevo.coach@demo.com", "password": "TempPass123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert login.json()["debe_cambiar_password"] is True

    H = {"Authorization": f"Bearer {token}"}
    # Cambiar la contraseña (actual = temporal)
    r = client.post("/auth/cambiar-password", headers=H, json={
        "password_actual": "TempPass123", "password_nueva": "miClaveNueva456",
    })
    assert r.status_code == 200

    # Ahora entra con la nueva y ya no se le exige cambio
    login2 = client.post("/auth/login", json={"correo": "nuevo.coach@demo.com", "password": "miClaveNueva456"})
    assert login2.status_code == 200 and login2.json()["debe_cambiar_password"] is False


def test_rechazar_solicitud(client, auth_admin):
    sid = _crear_solicitud(client, correo="rechazado@demo.com").json()["id"]
    r = client.post(f"/solicitudes/{sid}/rechazar", headers=auth_admin, json={"motivo": "Documento ilegible"})
    assert r.status_code == 200 and r.json()["estado"] == "rechazada"


def test_publico_inicio_sin_token(client):
    r = client.get("/publico/inicio")
    assert r.status_code == 200
    cuerpo = r.json()
    assert "proximos_partidos" in cuerpo and "torneos_activos" in cuerpo and "goleadores_top" in cuerpo
