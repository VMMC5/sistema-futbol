"""Reglas del MockGateway: tarjeta aprueba/rechaza y transferencia queda pendiente."""
from decimal import Decimal

from app.gateway import MockGateway


def test_tarjeta_aprobada():
    g = MockGateway()
    r = g.charge(Decimal("200.00"), "tarjeta", {"numero": "4111111111111234", "titular": "Ana"})
    assert r.estado == "completado"
    assert r.referencia.startswith("MOCK-")
    assert r.referencia.endswith("1234")   # ultimos 4 digitos


def test_tarjeta_rechazada_termina_en_0000():
    g = MockGateway()
    r = g.charge(Decimal("200.00"), "tarjeta", {"numero": "4111111111110000", "titular": "Ana"})
    assert r.estado == "fallido"
    assert r.motivo is not None


def test_transferencia_queda_pendiente():
    g = MockGateway()
    r = g.charge(Decimal("500.00"), "transferencia", None)
    assert r.estado == "pendiente"
    assert r.referencia.startswith("TRF-")
