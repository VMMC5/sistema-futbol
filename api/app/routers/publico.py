"""
Endpoints públicos (sin autenticación) para la app de cara al público.

- /publico/inicio                      -> próximos partidos + resumen
- /publico/torneos                     -> torneos activos y próximos
- /publico/torneos/{id}                -> detalle de un torneo
- /publico/torneos/{id}/tabla          -> tabla de posiciones
- /publico/torneos/{id}/partidos       -> partidos del torneo
- /publico/torneos/{id}/goleadores     -> goleadores del torneo
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, stats
from app.schemas import FilaTabla, GoleadorOut, PartidoOut

router = APIRouter()


def _resumen_torneo(db: Session, t: models.Torneo) -> dict:
    conteos = stats.equipos_y_partidos(db, t.id)
    return {
        "id": t.id,
        "nombre": t.nombre,
        "tipo": t.tipo,
        "estado": t.estado,
        "sede_nombre": t.sede.nombre if t.sede else None,
        "descripcion": t.descripcion,
        "fecha_inicio": t.fecha_inicio.isoformat() if t.fecha_inicio else None,
        "fecha_fin": t.fecha_fin.isoformat() if t.fecha_fin else None,
        "fecha_cierre_inscripciones": (
            t.fecha_cierre_inscripciones.isoformat() if t.fecha_cierre_inscripciones else None
        ),
        "cuota_inscripcion": float(t.cuota_inscripcion) if t.cuota_inscripcion is not None else None,
        "premio": t.premio,
        "cupo_maximo": t.cupo_maximo,
        **conteos,
    }


@router.get("/inicio")
def inicio(db: Session = Depends(get_db)):
    proximos = (
        db.query(models.Partido)
        .options(*models.CARGA_PARTIDO)
        .filter(models.Partido.estado.in_(["programado", "en_juego"]))
        .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora)
        .limit(5)
        .all()
    )
    torneos_activos = [
        _resumen_torneo(db, t)
        for t in (
            db.query(models.Torneo)
            .options(joinedload(models.Torneo.sede))
            .filter(models.Torneo.estado == "en_curso")
            .all()
        )
    ]
    return {
        "proximos_partidos": [PartidoOut.model_validate(p) for p in proximos],
        "torneos_activos": torneos_activos,
        "goleadores_top": [GoleadorOut(**g) for g in stats.goleadores(db, limit=5)],
    }


@router.get("/torneos")
def listar_torneos(db: Session = Depends(get_db)):
    activos, proximos = [], []
    orden = db.query(models.Torneo).order_by(
        models.Torneo.fecha_inicio.is_(None), models.Torneo.fecha_inicio
    ).all()
    for t in orden:
        resumen = _resumen_torneo(db, t)
        if t.estado == "en_curso":
            activos.append(resumen)
        elif t.estado == "programado":
            proximos.append(resumen)
    return {"activos": activos, "proximos": proximos}


@router.get("/torneos/{torneo_id}")
def ver_torneo(torneo_id: int, db: Session = Depends(get_db)):
    t = db.get(models.Torneo, torneo_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return _resumen_torneo(db, t)


@router.get("/torneos/{torneo_id}/tabla", response_model=list[FilaTabla])
def tabla(torneo_id: int, db: Session = Depends(get_db)):
    if db.get(models.Torneo, torneo_id) is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return stats.calcular_tabla(db, torneo_id)


@router.get("/torneos/{torneo_id}/partidos", response_model=list[PartidoOut])
def partidos_torneo(torneo_id: int, db: Session = Depends(get_db)):
    if db.get(models.Torneo, torneo_id) is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return (
        db.query(models.Partido)
        .options(*models.CARGA_PARTIDO)
        .filter(models.Partido.torneo_id == torneo_id)
        .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora, models.Partido.id)
        .all()
    )


@router.get("/torneos/{torneo_id}/goleadores", response_model=list[GoleadorOut])
def goleadores_torneo(torneo_id: int, db: Session = Depends(get_db)):
    if db.get(models.Torneo, torneo_id) is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return [GoleadorOut(**g) for g in stats.goleadores(db, torneo_id=torneo_id, limit=20)]
