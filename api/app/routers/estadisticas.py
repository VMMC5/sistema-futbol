"""
Estadísticas — calculadas a partir de los datos existentes (no hay tablas nuevas).

- Goleadores: cuenta los eventos de tipo 'gol' por jugador.
- Tarjetas: cuenta amarillas y rojas por jugador.
- Tabla de posiciones: se reconstruye recorriendo los partidos FINALIZADOS de un
  torneo y aplicando el sistema de puntos (3 por victoria, 1 por empate, 0 por derrota).

Todas son de solo lectura y accesibles para cualquier usuario autenticado.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user
from app.schemas import FilaTabla, GoleadorOut, TarjetasJugadorOut

router = APIRouter()


@router.get("/goleadores", response_model=list[GoleadorOut])
def goleadores(
    torneo_id: int | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    consulta = (
        db.query(
            models.Usuario.id,
            models.Usuario.nombre,
            func.count(models.EventoPartido.id).label("goles"),
        )
        .join(models.EventoPartido, models.EventoPartido.jugador_id == models.Usuario.id)
        .join(models.Partido, models.EventoPartido.partido_id == models.Partido.id)
        .filter(models.EventoPartido.tipo == "gol")
        .filter(or_(models.EventoPartido.subtipo.is_(None), models.EventoPartido.subtipo != "autogol"))
    )
    if torneo_id:
        consulta = consulta.filter(models.Partido.torneo_id == torneo_id)

    filas = (
        consulta.group_by(models.Usuario.id, models.Usuario.nombre)
        .order_by(func.count(models.EventoPartido.id).desc())
        .limit(limit)
        .all()
    )
    return [GoleadorOut(jugador_id=f.id, nombre=f.nombre, goles=int(f.goles)) for f in filas]


@router.get("/tarjetas", response_model=list[TarjetasJugadorOut])
def tarjetas(
    torneo_id: int | None = None,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    amarillas = func.sum(case((models.EventoPartido.tipo == "tarjeta_amarilla", 1), else_=0))
    rojas = func.sum(case((models.EventoPartido.tipo == "tarjeta_roja", 1), else_=0))

    consulta = (
        db.query(
            models.Usuario.id,
            models.Usuario.nombre,
            amarillas.label("amarillas"),
            rojas.label("rojas"),
        )
        .join(models.EventoPartido, models.EventoPartido.jugador_id == models.Usuario.id)
        .join(models.Partido, models.EventoPartido.partido_id == models.Partido.id)
        .filter(models.EventoPartido.tipo.in_(["tarjeta_amarilla", "tarjeta_roja"]))
    )
    if torneo_id:
        consulta = consulta.filter(models.Partido.torneo_id == torneo_id)

    filas = (
        consulta.group_by(models.Usuario.id, models.Usuario.nombre)
        .order_by(rojas.desc(), amarillas.desc())
        .all()
    )
    return [
        TarjetasJugadorOut(
            jugador_id=f.id, nombre=f.nombre,
            amarillas=int(f.amarillas or 0), rojas=int(f.rojas or 0),
        )
        for f in filas
    ]


@router.get("/torneos/{torneo_id}/tabla", response_model=list[FilaTabla])
def tabla_de_posiciones(
    torneo_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    if db.get(models.Torneo, torneo_id) is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")

    partidos = db.query(models.Partido).filter(models.Partido.torneo_id == torneo_id).all()

    # Inicializar a cero todos los equipos que aparecen en el torneo
    tabla: dict[int, dict] = {}

    def _asegurar(equipo_id):
        if equipo_id and equipo_id not in tabla:
            tabla[equipo_id] = {
                "pj": 0, "pg": 0, "pe": 0, "pp": 0,
                "gf": 0, "gc": 0, "puntos": 0,
            }

    for p in partidos:
        _asegurar(p.equipo_local_id)
        _asegurar(p.equipo_visitante_id)

        # Solo los partidos finalizados cuentan para la tabla
        if p.estado != "finalizado" or not p.equipo_local_id or not p.equipo_visitante_id:
            continue

        gl, gv = p.goles_local, p.goles_visitante
        local, visit = tabla[p.equipo_local_id], tabla[p.equipo_visitante_id]

        local["pj"] += 1; visit["pj"] += 1
        local["gf"] += gl; local["gc"] += gv
        visit["gf"] += gv; visit["gc"] += gl

        if gl > gv:
            local["pg"] += 1; local["puntos"] += 3
            visit["pp"] += 1
        elif gl < gv:
            visit["pg"] += 1; visit["puntos"] += 3
            local["pp"] += 1
        else:
            local["pe"] += 1; visit["pe"] += 1
            local["puntos"] += 1; visit["puntos"] += 1

    # Nombres de los equipos
    nombres = {
        e.id: e.nombre
        for e in db.query(models.Equipo).filter(models.Equipo.id.in_(tabla.keys())).all()
    } if tabla else {}

    filas = [
        FilaTabla(
            equipo_id=eid, equipo=nombres.get(eid, f"Equipo {eid}"),
            pj=d["pj"], pg=d["pg"], pe=d["pe"], pp=d["pp"],
            gf=d["gf"], gc=d["gc"], dg=d["gf"] - d["gc"], puntos=d["puntos"],
        )
        for eid, d in tabla.items()
    ]

    # Orden: puntos, luego diferencia de goles, luego goles a favor
    filas.sort(key=lambda f: (f.puntos, f.dg, f.gf), reverse=True)
    return filas
