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
from app import notificaciones_service
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


def _notificar(db: Session, usuario_id: int, titulo: str, mensaje: str,
               background_tasks=None) -> None:
    notificaciones_service.crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)


def _procesar(db: Session, usuario: models.Usuario, monto: Decimal, concepto: str,
              datos: PagoCreate, gateway: PaymentGateway):
    datos_tarjeta = None
    if datos.metodo == "tarjeta":
        datos_tarjeta = {"numero": datos.tarjeta.numero, "titular": datos.tarjeta.titular}
    resultado = gateway.charge(monto, datos.metodo, datos_tarjeta)

    pago = models.Pago(
        usuario_id=usuario.id, monto=monto, metodo=datos.metodo,
        estado=resultado.estado, referencia=resultado.referencia, concepto=concepto,
    )
    if resultado.estado == "completado":
        pago.completado_en = datetime.now(timezone.utc)
    db.add(pago)
    db.flush()
    return pago, resultado


def pagar_reserva(db: Session, usuario: models.Usuario, reserva: models.Reserva,
                  datos: PagoCreate, gateway: PaymentGateway | None = None,
                  background_tasks=None) -> models.Pago:
    gateway = gateway or _gateway

    if reserva.pago_id:
        previo = db.get(models.Pago, reserva.pago_id)
        if previo and previo.estado in ("completado", "pendiente"):
            raise HTTPException(status_code=409, detail="La reserva ya tiene un pago en curso o completado")

    if reserva.estado != "pendiente":
        raise HTTPException(status_code=409, detail="Solo se puede pagar una reserva pendiente")

    monto = calcular_monto_reserva(reserva.cancha, reserva.hora_inicio, reserva.hora_fin)
    concepto = f"Reserva {reserva.cancha.nombre} · {reserva.fecha} {reserva.hora_inicio:%H:%M}"
    pago, resultado = _procesar(db, usuario, monto, concepto, datos, gateway)

    if resultado.estado == "completado":
        reserva.pago_id = pago.id
        reserva.estado = "confirmada"
        _notificar(db, usuario.id, "Pago confirmado",
                   f"Tu {concepto} quedó pagada. Folio {pago.referencia}.", background_tasks)
    elif resultado.estado == "pendiente":
        reserva.pago_id = pago.id
        _notificar(db, usuario.id, "Pago en revisión",
                   f"Registramos tu transferencia por {concepto}. Pendiente de confirmación.", background_tasks)

    db.commit()
    if resultado.estado == "fallido":
        raise HTTPException(status_code=402, detail=resultado.motivo or "Pago rechazado")
    db.refresh(pago)
    return pago


def pagar_inscripcion(db: Session, usuario: models.Usuario, inscripcion: models.Inscripcion,
                      datos: PagoCreate, gateway: PaymentGateway | None = None,
                      background_tasks=None) -> models.Pago:
    gateway = gateway or _gateway

    if inscripcion.pago_id:
        previo = db.get(models.Pago, inscripcion.pago_id)
        if previo and previo.estado in ("completado", "pendiente"):
            raise HTTPException(status_code=409, detail="La inscripción ya tiene un pago en curso o completado")

    if inscripcion.estado != "pendiente":
        raise HTTPException(status_code=409, detail="Solo se puede pagar una inscripción pendiente")

    monto = calcular_monto_inscripcion(inscripcion.torneo)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="Esta inscripción no requiere pago")

    concepto = f"Inscripción {inscripcion.equipo.nombre} · {inscripcion.torneo.nombre}"
    pago, resultado = _procesar(db, usuario, monto, concepto, datos, gateway)

    if resultado.estado == "completado":
        inscripcion.pago_id = pago.id
        inscripcion.estado = "aceptada"
        _notificar(db, usuario.id, "Pago confirmado",
                   f"Tu {concepto} quedó pagada. Folio {pago.referencia}.", background_tasks)
    elif resultado.estado == "pendiente":
        inscripcion.pago_id = pago.id
        _notificar(db, usuario.id, "Pago en revisión",
                   f"Registramos tu transferencia por {concepto}. Pendiente de confirmación.", background_tasks)

    db.commit()
    if resultado.estado == "fallido":
        raise HTTPException(status_code=402, detail=resultado.motivo or "Pago rechazado")
    db.refresh(pago)
    return pago


def confirmar_pago(db: Session, pago: models.Pago, background_tasks=None) -> models.Pago:
    """El superadmin confirma una transferencia pendiente."""
    if pago.metodo != "transferencia" or pago.estado != "pendiente":
        raise HTTPException(status_code=409,
                            detail="Solo se confirma una transferencia pendiente")

    if pago.reserva is not None and pago.reserva.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La reserva vinculada ya no está pendiente")
    if pago.inscripcion is not None and pago.inscripcion.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La inscripción vinculada ya no está pendiente")

    pago.estado = "completado"
    pago.completado_en = datetime.now(timezone.utc)

    if pago.reserva is not None:
        pago.reserva.estado = "confirmada"
    if pago.inscripcion is not None:
        pago.inscripcion.estado = "aceptada"

    _notificar(db, pago.usuario_id, "Pago confirmado",
               f"Tu pago ({pago.concepto}) fue confirmado. Folio {pago.referencia}.", background_tasks)
    db.commit()
    db.refresh(pago)
    return pago
