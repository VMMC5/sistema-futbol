"""
Canchas — CRUD completo.

Lectura para cualquier usuario autenticado; creación/edición/borrado solo
para el superadmin. No se permite borrar una cancha con reservas o partidos
asociados (rompería las llaves foráneas).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user, require_roles
from app.schemas import CanchaCreate, CanchaOut, CanchaUpdate

router = APIRouter()


def _obtener_cancha(db: Session, cancha_id: int) -> models.Cancha:
    cancha = db.get(models.Cancha, cancha_id)
    if cancha is None:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    return cancha


def _validar_sede(db: Session, sede_id: int):
    if db.get(models.Sede, sede_id) is None:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")


@router.get("", response_model=list[CanchaOut])
def listar_canchas(
    sede_id: int | None = None,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Cancha)
    if sede_id:
        consulta = consulta.filter(models.Cancha.sede_id == sede_id)
    return consulta.order_by(models.Cancha.nombre).all()


@router.get("/{cancha_id}/disponibilidad")
def disponibilidad(
    cancha_id: int,
    fecha: str,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    """Horas ya ocupadas (hora_inicio) de una cancha en una fecha, para que el
    cliente deshabilite esos espacios. No expone quién reservó."""
    _obtener_cancha(db, cancha_id)
    reservas = (
        db.query(models.Reserva)
        .filter(
            models.Reserva.cancha_id == cancha_id,
            models.Reserva.fecha == fecha,
            models.Reserva.estado != "cancelada",
        )
        .all()
    )
    ocupados = [r.hora_inicio.strftime("%H:%M") for r in reservas]
    return {"fecha": fecha, "ocupados": ocupados}


@router.get("/{cancha_id}", response_model=CanchaOut)
def ver_cancha(
    cancha_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    return _obtener_cancha(db, cancha_id)


@router.post("", response_model=CanchaOut, status_code=status.HTTP_201_CREATED)
def crear_cancha(
    datos: CanchaCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    _validar_sede(db, datos.sede_id)
    cancha = models.Cancha(**datos.model_dump())
    db.add(cancha)
    db.commit()
    db.refresh(cancha)
    return cancha


@router.put("/{cancha_id}", response_model=CanchaOut)
def actualizar_cancha(
    cancha_id: int,
    datos: CanchaUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    cancha = _obtener_cancha(db, cancha_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "sede_id" in cambios and cambios["sede_id"] is not None:
        _validar_sede(db, cambios["sede_id"])

    for campo, valor in cambios.items():
        setattr(cancha, campo, valor)
    db.commit()
    db.refresh(cancha)
    return cancha


@router.delete("/{cancha_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cancha(
    cancha_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    cancha = _obtener_cancha(db, cancha_id)

    tiene_reservas = db.query(models.Reserva).filter_by(cancha_id=cancha_id).first() is not None
    tiene_partidos = db.query(models.Partido).filter_by(cancha_id=cancha_id).first() is not None
    if tiene_reservas or tiene_partidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la cancha tiene reservas o partidos asociados",
        )

    db.delete(cancha)
    db.commit()
