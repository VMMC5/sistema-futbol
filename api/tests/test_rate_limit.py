"""
Pruebas del rate limiting en /auth/login (anti fuerza bruta).

El limiter está apagado por defecto en las pruebas (ver conftest.py), así que
aquí se reactiva puntualmente y se restaura al terminar, para no contaminar el
contador en memoria de otras pruebas.
"""
import pytest

from app.rate_limit import limiter, LOGIN_RATE_LIMIT


@pytest.fixture
def limiter_activo():
    """Activa el limiter y limpia su contador antes y después del test."""
    limiter.reset()
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = False
        limiter.reset()


def _tope_por_minuto():
    # LOGIN_RATE_LIMIT tiene forma "N/minute"; extrae N.
    return int(LOGIN_RATE_LIMIT.split("/")[0])


def test_login_bloquea_tras_superar_el_tope(client, limiter_activo):
    """Al pasarse del límite por IP, el login responde 429 en vez de 401."""
    tope = _tope_por_minuto()
    credenciales = {"correo": "atacante@demo.com", "password": "malísima"}

    # Los primeros 'tope' intentos son credenciales inválidas -> 401.
    for _ in range(tope):
        r = client.post("/auth/login", json=credenciales)
        assert r.status_code == 401

    # El siguiente intento supera el tope -> 429 (Too Many Requests).
    r = client.post("/auth/login", json=credenciales)
    assert r.status_code == 429


def test_login_no_se_limita_cuando_esta_desactivado(client):
    """Con el limiter apagado (comportamiento por defecto en tests) no hay 429."""
    credenciales = {"correo": "atacante@demo.com", "password": "malísima"}
    codigos = {
        client.post("/auth/login", json=credenciales).status_code
        for _ in range(_tope_por_minuto() + 5)
    }
    assert codigos == {401}
