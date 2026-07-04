"""Cálculo de monto en el servidor (nunca lo envía el cliente)."""
from datetime import time
from decimal import Decimal
from types import SimpleNamespace

from app import pagos_service


def test_monto_reserva_una_hora():
    cancha = SimpleNamespace(precio_hora=Decimal("200.00"), nombre="Cancha 1")
    monto = pagos_service.calcular_monto_reserva(cancha, time(10, 0), time(11, 0))
    assert monto == Decimal("200.00")


def test_monto_reserva_hora_y_media():
    cancha = SimpleNamespace(precio_hora=Decimal("200.00"), nombre="Cancha 1")
    monto = pagos_service.calcular_monto_reserva(cancha, time(10, 0), time(11, 30))
    assert monto == Decimal("300.00")


def test_monto_inscripcion():
    torneo = SimpleNamespace(cuota_inscripcion=Decimal("500.00"))
    assert pagos_service.calcular_monto_inscripcion(torneo) == Decimal("500.00")


def test_monto_inscripcion_gratis():
    torneo = SimpleNamespace(cuota_inscripcion=None)
    assert pagos_service.calcular_monto_inscripcion(torneo) == Decimal("0")
