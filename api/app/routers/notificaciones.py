"""
Notificaciones del usuario: ver, marcar como leídas y eliminar.
Las generan otras partes del sistema (invitaciones, etc.).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import NotificacionOut

router = APIRouter()


@router.get("", response_model=list[NotificacionOut])
def listar(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    return (
        db.query(models.Notificacion)
        .filter_by(usuario_id=usuario.id)
        .order_by(models.Notificacion.creada_en.desc(), models.Notificacion.id.desc())
        .all()
    )


@router.post("/marcar-leidas")
def marcar_leidas(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    db.query(models.Notificacion).filter_by(usuario_id=usuario.id, leida=False).update({"leida": True})
    db.commit()
    return {"ok": True}


@router.delete("/{notificacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(notificacion_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    n = db.get(models.Notificacion, notificacion_id)
    if n is None or n.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    db.delete(n)
    db.commit()
