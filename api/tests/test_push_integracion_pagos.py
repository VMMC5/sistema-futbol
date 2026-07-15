"""Un pago de reserva confirmado debe encolar un push al pagador."""
from app import models, notificaciones_service as ns


def _login(client, correo, password):
    tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_pago_reserva_encola_push(client, db_session, monkeypatch):
    monkeypatch.setattr(ns, "SessionLocal", db_session)
    capturado = {}
    monkeypatch.setattr(ns, "_post_expo", lambda m: (capturado.setdefault("m", m), [])[1])

    h = _login(client, "miembro@demo.com", "miembropass123")
    client.post("/notificaciones/dispositivos", headers=h,
                json={"token": "ExponentPushToken[pagador]", "plataforma": "ios"})

    # Reserva sobre la Cancha 1 (precio 200, sembrada en conftest)
    reserva = client.post("/reservas", headers=h, json={
        "cancha_id": 1, "fecha": "2027-01-01", "hora_inicio": "10:00", "hora_fin": "11:00",
    }).json()

    # Pago con tarjeta (el MockGateway aprueba las tarjetas válidas)
    r = client.post(f"/pagos/reserva/{reserva['id']}", headers=h, json={
        "metodo": "tarjeta",
        "tarjeta": {"numero": "4111111111111111", "exp_mes": 12, "exp_anio": 2030,
                    "cvv": "123", "titular": "Miembro Uno"},
    })
    assert r.status_code == 201

    assert capturado["m"][0]["to"] == "ExponentPushToken[pagador]"
    assert capturado["m"][0]["title"] == "Pago confirmado"
