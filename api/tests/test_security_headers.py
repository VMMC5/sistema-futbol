"""
Pruebas de las cabeceras de seguridad de la API.

Incluyen el caso de /docs: Swagger carga sus assets de un CDN, así que una CSP
estricta lo dejaría en blanco. Debe recibir una política distinta.
"""
import pytest

from app import security_headers


@pytest.fixture(autouse=True)
def sin_produccion(monkeypatch):
    """Por defecto las pruebas corren como desarrollo (sin HSTS)."""
    monkeypatch.delenv("APP_ENV", raising=False)


def test_cabeceras_basicas_en_endpoints(client):
    r = client.get("/")

    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"


def test_csp_estricta_en_endpoints_json(client):
    """Un endpoint JSON no necesita cargar nada: la CSP más restrictiva posible."""
    r = client.get("/")

    assert r.headers["Content-Security-Policy"] == security_headers.CSP_API
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_csp_de_docs_permite_el_cdn_de_swagger(client):
    """/docs necesita su CDN o deja de renderizar."""
    r = client.get("/docs")

    csp = r.headers["Content-Security-Policy"]
    assert csp == security_headers.CSP_DOCS
    assert "https://cdn.jsdelivr.net" in csp
    # Y sigue sin poder embeberse en un iframe ajeno.
    assert "frame-ancestors 'none'" in csp


def test_sin_hsts_en_desarrollo(client):
    """En desarrollo se sirve por HTTP: HSTS dejaría el entorno inaccesible."""
    r = client.get("/")

    assert "Strict-Transport-Security" not in r.headers


def test_con_hsts_en_produccion(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    r = client.get("/")

    assert r.headers["Strict-Transport-Security"] == security_headers.HSTS
