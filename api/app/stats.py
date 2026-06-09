"""
Cálculos de estadísticas reutilizables (los usan el router de estadísticas
—privado— y el router público). Mantener la lógica en un solo lugar evita
duplicarla y que se desincronicen.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


def goleadores(db: Session, torneo_id: int | None = None, limit: int = 10) -> list[dict]:
    consulta = (
        db.query(
            models.Usuario.id,
            models.Usuario.nombre,
            func.count(models.EventoPartido.id).label("goles"),
        )
        .join(models.EventoPartido, models.EventoPartido.jugador_id == models.Usuario.id)
        .join(models.Partido, models.EventoPartido.partido_id == models.Partido.id)
        .filter(models.EventoPartido.tipo == "gol")
    )
    if torneo_id:
        consulta = consulta.filter(models.Partido.torneo_id == torneo_id)
    filas = (
        consulta.group_by(models.Usuario.id, models.Usuario.nombre)
        .order_by(func.count(models.EventoPartido.id).desc())
        .limit(limit)
        .all()
    )
    return [{"jugador_id": f.id, "nombre": f.nombre, "goles": int(f.goles)} for f in filas]


def calcular_tabla(db: Session, torneo_id: int) -> list[dict]:
    """Tabla de posiciones de un torneo a partir de sus partidos finalizados."""
    partidos = db.query(models.Partido).filter(models.Partido.torneo_id == torneo_id).all()

    tabla: dict[int, dict] = {}

    def _asegurar(equipo_id):
        if equipo_id and equipo_id not in tabla:
            tabla[equipo_id] = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "puntos": 0}

    for p in partidos:
        _asegurar(p.equipo_local_id)
        _asegurar(p.equipo_visitante_id)
        if p.estado != "finalizado" or not p.equipo_local_id or not p.equipo_visitante_id:
            continue

        gl, gv = p.goles_local, p.goles_visitante
        local, visit = tabla[p.equipo_local_id], tabla[p.equipo_visitante_id]
        local["pj"] += 1; visit["pj"] += 1
        local["gf"] += gl; local["gc"] += gv
        visit["gf"] += gv; visit["gc"] += gl
        if gl > gv:
            local["pg"] += 1; local["puntos"] += 3; visit["pp"] += 1
        elif gl < gv:
            visit["pg"] += 1; visit["puntos"] += 3; local["pp"] += 1
        else:
            local["pe"] += 1; visit["pe"] += 1; local["puntos"] += 1; visit["puntos"] += 1

    nombres = (
        {e.id: e.nombre for e in db.query(models.Equipo).filter(models.Equipo.id.in_(tabla.keys())).all()}
        if tabla else {}
    )
    filas = [
        {
            "equipo_id": eid, "equipo": nombres.get(eid, f"Equipo {eid}"),
            "pj": d["pj"], "pg": d["pg"], "pe": d["pe"], "pp": d["pp"],
            "gf": d["gf"], "gc": d["gc"], "dg": d["gf"] - d["gc"], "puntos": d["puntos"],
        }
        for eid, d in tabla.items()
    ]
    filas.sort(key=lambda f: (f["puntos"], f["dg"], f["gf"]), reverse=True)
    return filas


def equipos_y_partidos(db: Session, torneo_id: int) -> dict:
    """Cuenta equipos distintos que aparecen en el torneo y partidos jugados/total."""
    partidos = db.query(models.Partido).filter(models.Partido.torneo_id == torneo_id).all()
    equipos = set()
    jugados = 0
    for p in partidos:
        if p.equipo_local_id:
            equipos.add(p.equipo_local_id)
        if p.equipo_visitante_id:
            equipos.add(p.equipo_visitante_id)
        if p.estado == "finalizado":
            jugados += 1
    return {"equipos": len(equipos), "partidos_jugados": jugados, "partidos_total": len(partidos)}
