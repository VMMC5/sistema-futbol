"""
Notificaciones del usuario: ver, marcar como leídas y eliminar.
Las generan otras partes del sistema (invitaciones, etc.).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import NotificacionOut, DispositivoRegistro

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


# ---------------------------------------------------------------- dispositivos push
# Nota: estas rutas deben registrarse ANTES de DELETE /{notificacion_id}: ese
# path param no tiene tipo en la URL, así que "dispositivos" lo matchearía
# primero y fallaría la validación a int (422) en vez de caer a esta ruta.
@router.post("/dispositivos")
def registrar_dispositivo(
    datos: DispositivoRegistro,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Registra (o reasigna) el token de push del dispositivo actual."""
    disp = db.query(models.DispositivoPush).filter_by(token=datos.token).first()
    if disp is None:
        disp = models.DispositivoPush(token=datos.token)
        db.add(disp)
    disp.usuario_id = usuario.id
    disp.plataforma = datos.plataforma
    db.commit()
    return {"ok": True}


@router.delete("/dispositivos", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_dispositivo(
    token: str,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Baja del token (al cerrar sesión). Solo borra si es del usuario actual."""
    disp = db.query(models.DispositivoPush).filter_by(token=token, usuario_id=usuario.id).first()
    if disp is not None:
        db.delete(disp)
        db.commit()


@router.delete("/{notificacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(notificacion_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    n = db.get(models.Notificacion, notificacion_id)
    if n is None or n.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    db.delete(n)
    db.commit()
