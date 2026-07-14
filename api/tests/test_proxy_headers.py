"""
Detrás de nginx, la IP del cliente llega en X-Forwarded-For. Sin esto, el rate
limiting y la auditoría verían siempre la IP del proxy.

Pero confiar en esa cabecera sin estar detrás de un proxy permitiría a cualquiera
falsificar su IP para saltarse el rate limiting: por eso solo se confía cuando
TRUSTED_PROXIES está definida.
"""
import importlib
import logging

import pytest
from fastapi.testclient import TestClient

from app import audit
from app.database import get_db


def _app_con(monkeypatch, trusted_proxies, db_session):
    """Reconstruye la app con el valor dado de TRUSTED_PROXIES.

    Al recargar app.main con importlib.reload no se hereda el override de
    get_db del fixture `client`, así que aquí se aplica uno propio sobre la
    app recargada, apoyado en la SQLite en memoria de `db_session`, para no
    depender de la Postgres real de docker-compose (host "db").
    """
    if trusted_proxies is None:
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    else:
        monkeypatch.setenv("TRUSTED_PROXIES", trusted_proxies)

    import app.main
    importlib.reload(app.main)
    aplicacion = app.main.app

    def override_db():
        d = db_session()
        try:
            yield d
        finally:
            d.close()

    aplicacion.dependency_overrides[get_db] = override_db
    return aplicacion


def test_confia_en_x_forwarded_for_cuando_hay_proxy(monkeypatch, caplog, db_session):
    caplog.set_level(logging.INFO, logger="auditoria")
    aplicacion = _app_con(monkeypatch, "*", db_session)

    with TestClient(aplicacion) as cliente:
        cliente.post(
            "/auth/login",
            json={"correo": "nadie@demo.com", "password": "mala"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

    # La auditoría registra la IP real del cliente, no la del proxy.
    assert "ip=203.0.113.7" in caplog.text


def test_ignora_x_forwarded_for_sin_proxy(monkeypatch, caplog, db_session):
    """Sin proxy la cabecera es falsificable: debe ignorarse."""
    caplog.set_level(logging.INFO, logger="auditoria")
    aplicacion = _app_con(monkeypatch, None, db_session)

    with TestClient(aplicacion) as cliente:
        cliente.post(
            "/auth/login",
            json={"correo": "nadie@demo.com", "password": "mala"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

    assert "ip=203.0.113.7" not in caplog.text
