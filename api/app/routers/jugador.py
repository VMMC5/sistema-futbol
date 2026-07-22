"""
Panel del jugador: estadísticas personales (con filtro por torneo) y próximos
partidos de su equipo (para el calendario).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user

router = APIRouter()


def _equipos_del_jugador(db: Session, jugador_id: int) -> list[int]:
    filas = db.query(models.JugadorEquipo.equipo_id).filter_by(jugador_id=jugador_id).all()
    return [f.equipo_id for f in filas]


@router.get("/estadisticas")
def estadisticas(
    torneo_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    yo = usuario.id

    def base_eventos():
        q = (
            db.query(models.EventoPartido)
            .join(models.Partido, models.EventoPartido.partido_id == models.Partido.id)
        )
        if torneo_id:
            q = q.filter(models.Partido.torneo_id == torneo_id)
        return q

    goles = base_eventos().filter(
        models.EventoPartido.jugador_id == yo,
        models.EventoPartido.tipo == "gol",
        or_(models.EventoPartido.subtipo.is_(None), models.EventoPartido.subtipo != "autogol"),
    ).count()
    asistencias = base_eventos().filter(
        models.EventoPartido.jugador_secundario_id == yo, models.EventoPartido.tipo == "gol",
    ).count()
    amarillas = base_eventos().filter(
        models.EventoPartido.jugador_id == yo, models.EventoPartido.tipo == "tarjeta_amarilla",
    ).count()
    rojas = base_eventos().filter(
        models.EventoPartido.jugador_id == yo, models.EventoPartido.tipo == "tarjeta_roja",
    ).count()

    # Partidos finalizados del/los equipo(s) del jugador
    equipos = _equipos_del_jugador(db, yo)
    partidos_q = db.query(models.Partido).filter(models.Partido.estado == "finalizado")
    if equipos:
        partidos_q = partidos_q.filter(
            or_(models.Partido.equipo_local_id.in_(equipos), models.Partido.equipo_visitante_id.in_(equipos))
        )
    else:
        partidos_q = partidos_q.filter(False)
    if torneo_id:
        partidos_q = partidos_q.filter(models.Partido.torneo_id == torneo_id)
    partidos = partidos_q.order_by(models.Partido.fecha_hora, models.Partido.id).all()

    # Goles por jornada (por cada partido finalizado del equipo, goles del jugador)
    por_jornada = []
    for i, p in enumerate(partidos[-6:], start=1):
        g = sum(
            1 for e in p.eventos
            if e.jugador_id == yo and e.tipo == "gol" and (e.subtipo or "normal") != "autogol"
        )
        por_jornada.append({"etiqueta": f"J{i}", "goles": g})

    # Torneos donde ha jugado el equipo (para el filtro)
    torneos = []
    if equipos:
        filas = (
            db.query(models.Torneo.id, models.Torneo.nombre)
            .join(models.Partido, models.Partido.torneo_id == models.Torneo.id)
            .filter(or_(models.Partido.equipo_local_id.in_(equipos), models.Partido.equipo_visitante_id.in_(equipos)))
            .distinct()
            .all()
        )
        torneos = [{"id": f.id, "nombre": f.nombre} for f in filas]

    return {
        "goles": goles, "asistencias": asistencias, "amarillas": amarillas, "rojas": rojas,
        "partidos": len(partidos),
        "minutos_estimados": len(partidos) * 90,  # estimación (no se registran minutos exactos)
        "por_jornada": por_jornada,
        "torneos": torneos,
    }


@router.get("/proximos-partidos")
def proximos_partidos(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    equipos = _equipos_del_jugador(db, usuario.id)
    if not equipos:
        return []
    partidos = (
        db.query(models.Partido)
        .options(*models.CARGA_PARTIDO)
        .filter(
            or_(models.Partido.equipo_local_id.in_(equipos), models.Partido.equipo_visitante_id.in_(equipos)),
            models.Partido.estado.in_(["programado", "en_juego"]),
        )
        .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora)
        .all()
    )
    salida = []
    for p in partidos:
        local = p.equipo_local_id in equipos
        salida.append({
            "id": p.id,
            "rival": p.equipo_visitante_nombre if local else p.equipo_local_nombre,
            "fecha_hora": p.fecha_hora.isoformat() if p.fecha_hora else None,
            "torneo_nombre": p.torneo_nombre,
            "cancha_nombre": p.cancha_nombre,
            "estado": p.estado,
        })
    return salida
