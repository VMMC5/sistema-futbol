"""Pruebas del panel público y del flujo de solicitudes de registro."""
import re


def _jugador(client):
    client.post("/auth/register", json={"nombre": "Ana", "correo": "ana@demo.com", "password": "claveSegura123"})
    tok = client.post("/auth/login", json={"correo": "ana@demo.com", "password": "claveSegura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


# ---------- Panel público ----------
def test_inicio_es_publico(client):
    r = client.get("/publico/inicio")
    assert r.status_code == 200
    datos = r.json()
    assert "proximos_partidos" in datos
    assert "torneos_activos" in datos
    assert "goleadores_top" in datos


# ---------- Solicitudes ----------
def _documento_pdf():
    return {"documento": ("credencial.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")}


def test_crear_solicitud_es_publica(client):
    r = client.post("/solicitudes",
                    data={"nombre": "Coach Uno", "correo": "coach1@demo.com", "rol_solicitado": "entrenador", "telefono": "771"},
                    files=_documento_pdf())
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"


def test_solicitud_rol_invalido(client):
    r = client.post("/solicitudes",
                    data={"nombre": "X Y", "correo": "x@demo.com", "rol_solicitado": "presidente"},
                    files=_documento_pdf())
    assert r.status_code == 400


def test_solicitud_correo_malformado(client):
    # El correo debe tener formato válido (EmailStr), no basta con ser único.
    r = client.post("/solicitudes",
                    data={"nombre": "X Y", "correo": "correo-sin-arroba", "rol_solicitado": "arbitro"},
                    files=_documento_pdf())
    assert r.status_code == 422


def test_solicitud_documento_invalido(client):
    r = client.post("/solicitudes",
                    data={"nombre": "X Y", "correo": "x@demo.com", "rol_solicitado": "arbitro"},
                    files={"documento": ("nota.txt", b"hola", "text/plain")})
    assert r.status_code == 400


def test_solicitud_correo_ya_usuario(client):
    # admin@demo.com ya existe (sembrado)
    r = client.post("/solicitudes",
                    data={"nombre": "Admin Falso", "correo": "admin@demo.com", "rol_solicitado": "arbitro"},
                    files=_documento_pdf())
    assert r.status_code == 400


def test_listar_solicitudes_solo_admin(client):
    assert client.get("/solicitudes", headers=_jugador(client)).status_code == 403


def test_flujo_aceptacion_completo(client, auth_admin, monkeypatch):
    # Capturar el correo (en vez de enviarlo) para extraer la contraseña temporal
    import app.routers.solicitudes as sol
    capturado = {}
    monkeypatch.setattr(sol, "enviar_correo",
                        lambda destinatario, asunto, cuerpo: capturado.update(cuerpo=cuerpo))

    sid = client.post("/solicitudes",
                      data={"nombre": "Ref Nuevo", "correo": "refnuevo@demo.com", "rol_solicitado": "arbitro"},
                      files=_documento_pdf()).json()["id"]

    # El admin la ve entre las pendientes
    assert any(s["id"] == sid for s in client.get("/solicitudes", headers=auth_admin).json())

    # Aceptar -> crea usuario + envía credenciales
    r = client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin)
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"

    # Extraer la contraseña temporal del cuerpo del correo
    temp = re.search(r"temporal: (\S+)", capturado["cuerpo"]).group(1)

    # Login con la temporal -> debe pedir cambio de contraseña
    r = client.post("/auth/login", json={"correo": "refnuevo@demo.com", "password": temp})
    assert r.status_code == 200 and r.json()["debe_cambiar_password"] is True
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Cambiar la contraseña
    r = client.post("/auth/cambiar-password", headers=headers,
                    json={"password_actual": temp, "password_nueva": "miNuevaClave123"})
    assert r.status_code == 200

    # Nuevo login -> ya no pide cambio
    r = client.post("/auth/login", json={"correo": "refnuevo@demo.com", "password": "miNuevaClave123"})
    assert r.status_code == 200 and r.json()["debe_cambiar_password"] is False


def test_aceptar_dos_veces_falla(client, auth_admin, monkeypatch):
    import app.routers.solicitudes as sol
    monkeypatch.setattr(sol, "enviar_correo", lambda destinatario, asunto, cuerpo: None)

    sid = client.post("/solicitudes",
                      data={"nombre": "Doble", "correo": "doble@demo.com", "rol_solicitado": "entrenador"},
                      files=_documento_pdf()).json()["id"]
    assert client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin).status_code == 200
    # Segunda vez -> 409
    assert client.post(f"/solicitudes/{sid}/aceptar", headers=auth_admin).status_code == 409


def test_rechazar_solicitud(client, auth_admin, monkeypatch):
    import app.routers.solicitudes as sol
    monkeypatch.setattr(sol, "enviar_correo", lambda destinatario, asunto, cuerpo: None)

    sid = client.post("/solicitudes",
                      data={"nombre": "Rechazo", "correo": "rechazo@demo.com", "rol_solicitado": "arbitro"},
                      files=_documento_pdf()).json()["id"]
    r = client.post(f"/solicitudes/{sid}/rechazar", headers=auth_admin, json={"motivo": "Documento ilegible"})
    assert r.status_code == 200 and r.json()["estado"] == "rechazada"
