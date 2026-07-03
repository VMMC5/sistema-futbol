"""
Inscripción de equipos a torneos.

El entrenador dueño del equipo lo inscribe a un torneo. La inscripción nace
'pendiente'; pasa a 'aceptada' cuando se paga la cuota (router de pagos) — o
directo si el torneo no tiene cuota.

Reglas: el torneo no debe estar finalizado ni con inscripciones cerradas;
el equipo debe ser del entrenador; no se puede inscribir dos veces el mismo
equipo; se respeta el cupo máximo.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import InscripcionCreate, InscripcionOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


@router.post("", response_model=InscripcionOut, status_code=status.HTTP_201_CREATED)
def crear_inscripcion(
    datos: InscripcionCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    torneo = db.get(models.Torneo, datos.torneo_id)
    if torneo is None:
        raise HTTPException(status_code=400, detail="El torneo no existe")

    equipo = db.get(models.Equipo, datos.equipo_id)
    if equipo is None:
        raise HTTPException(status_code=400, detail="El equipo no existe")
    if not _es_admin(usuario) and equipo.entrenador_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo el entrenador del equipo puede inscribirlo")

    # Inscripciones abiertas
    if torneo.estado == "finalizado":
        raise HTTPException(status_code=409, detail="El torneo está finalizado")
    if torneo.fecha_cierre_inscripciones and date.today() > torneo.fecha_cierre_inscripciones:
        raise HTTPException(status_code=409, detail="Las inscripciones están cerradas")

    # No duplicar
    ya = (
        db.query(models.Inscripcion)
        .filter_by(torneo_id=datos.torneo_id, equipo_id=datos.equipo_id)
        .first()
    )
    if ya is not None:
        raise HTTPException(status_code=409, detail="El equipo ya está inscrito en este torneo")

    # Cupo
    if torneo.cupo_maximo is not None:
        inscritos = db.query(models.Inscripcion).filter_by(torneo_id=datos.torneo_id).count()
        if inscritos >= torneo.cupo_maximo:
            raise HTTPException(status_code=409, detail="El torneo llegó a su cupo máximo")

    inscripcion = models.Inscripcion(
        torneo_id=datos.torneo_id, equipo_id=datos.equipo_id, estado="pendiente",
    )
    db.add(inscripcion)
    db.commit()
    db.refresh(inscripcion)
    return inscripcion


@router.get("", response_model=list[InscripcionOut])
def listar_inscripciones(
    torneo_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Inscripcion)
    # Un entrenador ve las inscripciones de SUS equipos; el admin, todas.
    if not _es_admin(usuario):
        consulta = consulta.join(models.Equipo).filter(models.Equipo.entrenador_id == usuario.id)
    if torneo_id:
        consulta = consulta.filter(models.Inscripcion.torneo_id == torneo_id)
    return consulta.order_by(models.Inscripcion.id).all()
