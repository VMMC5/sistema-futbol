"""
Pruebas de la auditoría de eventos sensibles.

Lo más importante que se verifica aquí: que NUNCA se filtren secretos
(contraseñas, hashes ni tokens) a los logs.
"""
import logging

import pytest

from app import audit


@pytest.fixture
def logs_auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")
    return caplog


def test_login_exitoso_queda_auditado(client, logs_auditoria):
    r = client.post(
        "/auth/login",
        json={"correo": "admin@demo.com", "password": "adminpass123"},
    )
    assert r.status_code == 200

    registros = logs_auditoria.text
    assert audit.LOGIN_EXITOSO in registros
    assert "AUDIT" in registros


def test_login_fallido_queda_auditado_con_el_correo(client, logs_auditoria):
    """Un intento fallido deja rastro del correo probado, para investigar ataques."""
    r = client.post(
        "/auth/login",
        json={"correo": "atacante@demo.com", "password": "incorrecta"},
    )
    assert r.status_code == 401

    assert audit.LOGIN_FALLIDO in logs_auditoria.text
    assert "atacante@demo.com" in logs_auditoria.text


def test_la_auditoria_nunca_registra_la_contrasena(client, logs_auditoria):
    """Ni en el éxito ni en el fallo debe aparecer la contraseña en los logs."""
    client.post(
        "/auth/login",
        json={"correo": "admin@demo.com", "password": "adminpass123"},
    )
    client.post(
        "/auth/login",
        json={"correo": "admin@demo.com", "password": "SuperSecreta999"},
    )

    registros = logs_auditoria.text
    assert "adminpass123" not in registros
    assert "SuperSecreta999" not in registros


def test_cambio_de_password_no_registra_la_nueva(client, token_admin, logs_auditoria):
    r = client.post(
        "/auth/cambiar-password",
        json={"password_actual": "adminpass123", "password_nueva": "NuevaClave456"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200

    registros = logs_auditoria.text
    assert audit.PASSWORD_CAMBIADA in registros
    # El evento se registra, pero la contraseña nueva jamás.
    assert "NuevaClave456" not in registros


def test_registrar_omite_los_campos_vacios():
    """Una llamada mínima no debe inventar campos."""
    assert audit.ip_de(None) == "desconocida"
