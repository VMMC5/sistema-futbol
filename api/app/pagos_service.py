"""
Lógica de pagos (orquestación). El router solo hace HTTP + autorización;
aquí vive el cálculo de monto, el cobro contra el gateway, la confirmación
de reserva/inscripción y la notificación.

El monto se calcula SIEMPRE en el servidor a partir de la cancha/torneo,
nunca se toma del cliente.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.gateway import MockGateway, PaymentGateway
from app.schemas import PagoCreate

_gateway: PaymentGateway = MockGateway()

_DOS_DEC = Decimal("0.01")


def calcular_monto_reserva(cancha, hora_inicio, hora_fin) -> Decimal:
    if cancha.precio_hora is None:
        raise HTTPException(status_code=400, detail="La cancha no tiene precio configurado")
    inicio = datetime.combine(date.min, hora_inicio)
    fin = datetime.combine(date.min, hora_fin)
    horas = Decimal((fin - inicio).total_seconds()) / Decimal(3600)
    return (Decimal(cancha.precio_hora) * horas).quantize(_DOS_DEC, ROUND_HALF_UP)


def calcular_monto_inscripcion(torneo) -> Decimal:
    cuota = torneo.cuota_inscripcion
    if cuota is None or Decimal(cuota) <= 0:
        return Decimal("0")
    return Decimal(cuota).quantize(_DOS_DEC, ROUND_HALF_UP)
