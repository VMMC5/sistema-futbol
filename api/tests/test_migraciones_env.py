"""
Las migraciones necesitan DDL, así que corren con un usuario admin distinto al
que usa la API en runtime (limitado). En desarrollo no existe ese usuario admin,
y debe seguir funcionando con las credenciales de siempre.
"""
import os
import sys

import pytest


def _construir_url(monkeypatch, **variables):
    """Importa el helper de env.py con las variables dadas."""
    for nombre in ("DB_ADMIN_USER", "DB_ADMIN_PASSWORD", "DB_USER", "DB_PASSWORD",
                   "DB_HOST", "DB_PORT", "DB_NAME"):
        monkeypatch.delenv(nombre, raising=False)
    for nombre, valor in variables.items():
        monkeypatch.setenv(nombre, valor)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "migrations"))
    from url_bd import url_de_migraciones  # noqa: E402
    return url_de_migraciones()


def test_usa_el_usuario_admin_cuando_existe(monkeypatch):
    url = _construir_url(
        monkeypatch,
        DB_ADMIN_USER="admin", DB_ADMIN_PASSWORD="secreta",
        DB_USER="app", DB_PASSWORD="limitada",
        DB_HOST="db", DB_NAME="torneos",
    )

    assert "admin:secreta@" in url
    # El usuario limitado de la API no se usa para migrar.
    assert "app:limitada@" not in url


def test_reserva_al_usuario_normal_en_desarrollo(monkeypatch):
    """En local no hay usuario admin: se usan las credenciales de siempre."""
    url = _construir_url(
        monkeypatch,
        DB_USER="postgres", DB_PASSWORD="clave",
        DB_HOST="db", DB_NAME="torneos",
    )

    assert "postgres:clave@" in url
