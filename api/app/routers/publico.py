"""
Endpoints públicos (sin autenticación) para la pantalla principal de la app.

Muestra la información más relevante del sistema a cualquier visitante:
próximos partidos y torneos activos con un pequeño resumen estadístico.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import GoleadorOut, PartidoOut, TorneoOut

router = APIRouter()


@router.get("/inicio")
def inicio(db: Session = Depends(get_db)):
    # Próximos partidos (programados o en juego), por fecha
    proximos = (
        db.query(models.Partido)
        .filter(models.Partido.estado.in_(["programado", "en_juego"]))
        .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora)
        .limit(5)
        .all()
    )

    # Torneos activos con un resumen (partidos jugados y goles)
    torneos_activos = []
    for t in db.query(models.Torneo).filter(models.Torneo.estado == "en_curso").all():
        finalizados = [p for p in t.partidos if p.estado == "finalizado"]
        goles = sum((p.goles_local + p.goles_visitante) for p in finalizados)
        datos = TorneoOut.model_validate(t).model_dump()
        datos["partidos_jugados"] = len(finalizados)
        datos["goles_totales"] = goles
        torneos_activos.append(datos)

    # Top 5 goleadores global
    from sqlalchemy import func
    filas = (
        db.query(models.Usuario.id, models.Usuario.nombre, func.count(models.EventoPartido.id).label("g"))
        .join(models.EventoPartido, models.EventoPartido.jugador_id == models.Usuario.id)
        .filter(models.EventoPartido.tipo == "gol")
        .group_by(models.Usuario.id, models.Usuario.nombre)
        .order_by(func.count(models.EventoPartido.id).desc())
        .limit(5)
        .all()
    )
    goleadores = [GoleadorOut(jugador_id=f.id, nombre=f.nombre, goles=int(f.g)) for f in filas]

    return {
        "proximos_partidos": [PartidoOut.model_validate(p) for p in proximos],
        "torneos_activos": torneos_activos,
        "goleadores_top": goleadores,
    }
