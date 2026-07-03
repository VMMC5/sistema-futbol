"""
Pagos en línea (pasarela simulada). Paga reservas e inscripciones a torneos.

Reglas de acceso:
- Pagar una reserva: su dueño.
- El monto lo calcula el servidor (nunca el cliente).
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, pagos_service, recibo_pdf
from app.deps import get_current_user, require_roles
from app.schemas import PagoCreate, PagoOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


@router.post("/reserva/{reserva_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_reserva(
    reserva_id: int,
    datos: PagoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = db.get(models.Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una reserva ajena")
    return pagos_service.pagar_reserva(db, usuario, reserva, datos)


@router.post("/inscripcion/{inscripcion_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_inscripcion(
    inscripcion_id: int,
    datos: PagoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    inscripcion = db.get(models.Inscripcion, inscripcion_id)
    if inscripcion is None:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    # Paga el entrenador dueño del equipo (o el admin)
    if not _es_admin(usuario) and inscripcion.equipo.entrenador_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una inscripción ajena")
    return pagos_service.pagar_inscripcion(db, usuario, inscripcion, datos)


@router.post("/{pago_id}/confirmar", response_model=PagoOut)
def confirmar_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    pago = db.get(models.Pago, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pagos_service.confirmar_pago(db, pago)


@router.get("", response_model=list[PagoOut])
def historial_pagos(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Pago)
    if not _es_admin(usuario):
        consulta = consulta.filter(models.Pago.usuario_id == usuario.id)
    return consulta.order_by(models.Pago.id.desc()).all()


def _pago_visible(db: Session, pago_id: int, usuario: models.Usuario) -> models.Pago:
    pago = db.get(models.Pago, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if not _es_admin(usuario) and pago.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes ver un pago ajeno")
    return pago


@router.get("/{pago_id}", response_model=PagoOut)
def ver_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    return _pago_visible(db, pago_id, usuario)


@router.get("/{pago_id}/recibo.pdf")
def recibo(
    pago_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    pago = _pago_visible(db, pago_id, usuario)
    if pago.estado != "completado":
        raise HTTPException(status_code=409, detail="El recibo solo está disponible para pagos completados")
    contenido = recibo_pdf.generar(pago)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pago.id}.pdf"'},
    )
