"""
Sedes — listado y gestión.

Lectura para cualquier usuario autenticado (el panel la usa para poblar
desplegables); creación reservada al superadmin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user, require_roles
from app.schemas import SedeCreate, SedeOut, SedeUpdate

router = APIRouter()


@router.get("", response_model=list[SedeOut])
def listar_sedes(
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    return db.query(models.Sede).order_by(models.Sede.nombre).all()


@router.get("/{sede_id}", response_model=SedeOut)
def ver_sede(
    sede_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    sede = db.get(models.Sede, sede_id)
    if sede is None:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    return sede


@router.post("", response_model=SedeOut, status_code=status.HTTP_201_CREATED)
def crear_sede(
    datos: SedeCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    sede = models.Sede(**datos.model_dump())
    db.add(sede)
    db.commit()
    db.refresh(sede)
    return sede


@router.put("/{sede_id}", response_model=SedeOut)
def actualizar_sede(
    sede_id: int,
    datos: SedeUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    sede = db.get(models.Sede, sede_id)
    if sede is None:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(sede, campo, valor)
    db.commit()
    db.refresh(sede)
    return sede


@router.delete("/{sede_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_sede(
    sede_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    sede = db.get(models.Sede, sede_id)
    if sede is None:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    # No permitir borrar si tiene canchas o torneos asociados (romperia las FK)
    tiene_canchas = db.query(models.Cancha).filter_by(sede_id=sede_id).first() is not None
    tiene_torneos = db.query(models.Torneo).filter_by(sede_id=sede_id).first() is not None
    if tiene_canchas or tiene_torneos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la sede tiene canchas o torneos asociados",
        )

    db.delete(sede)
    db.commit()
