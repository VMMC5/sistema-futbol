"""
Invitaciones a equipo desde el lado del JUGADOR: ver las pendientes (es la
"notificación" en la app), aceptar o rechazar.

- Al aceptar: el jugador entra a la plantilla del equipo. No puede salir por sí
  mismo; solo el entrenador puede quitarlo.
- Un jugador solo puede pertenecer a un equipo: al aceptar uno, las demás
  invitaciones pendientes se marcan como rechazadas.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import InvitacionOut

router = APIRouter()


def _invitacion_propia(db: Session, invitacion_id: int, usuario: models.Usuario) -> models.InvitacionEquipo:
    inv = db.get(models.InvitacionEquipo, invitacion_id)
    if inv is None or inv.jugador_id != usuario.id:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return inv


@router.get("/mias", response_model=list[InvitacionOut])
def mis_invitaciones(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    return (
        db.query(models.InvitacionEquipo)
        .filter_by(jugador_id=usuario.id, estado="pendiente")
        .order_by(models.InvitacionEquipo.id.desc())
        .all()
    )


@router.post("/{invitacion_id}/aceptar", response_model=InvitacionOut)
def aceptar(invitacion_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    inv = _invitacion_propia(db, invitacion_id, usuario)
    if inv.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La invitación ya fue respondida")

    # El jugador no debe pertenecer ya a un equipo
    if db.query(models.JugadorEquipo).filter_by(jugador_id=usuario.id).first():
        raise HTTPException(status_code=409, detail="Ya perteneces a un equipo")

    db.add(models.JugadorEquipo(equipo_id=inv.equipo_id, jugador_id=usuario.id))
    inv.estado = "aceptada"
    # Rechaza el resto de invitaciones pendientes del jugador
    otras = (
        db.query(models.InvitacionEquipo)
        .filter(
            models.InvitacionEquipo.jugador_id == usuario.id,
            models.InvitacionEquipo.estado == "pendiente",
            models.InvitacionEquipo.id != inv.id,
        ).all()
    )
    for o in otras:
        o.estado = "rechazada"
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invitacion_id}/rechazar", response_model=InvitacionOut)
def rechazar(invitacion_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    inv = _invitacion_propia(db, invitacion_id, usuario)
    if inv.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La invitación ya fue respondida")
    inv.estado = "rechazada"
    db.commit()
    db.refresh(inv)
    return inv
