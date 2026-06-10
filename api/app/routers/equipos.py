"""
Equipos del entrenador: gestión de equipos y su plantilla, resumen para el
panel de inicio y estadísticas del equipo.

Reglas:
- Crear equipos: entrenador o superadmin.
- Ver/editar/borrar un equipo: su entrenador dueño (o superadmin).
- La plantilla admite jugadores de texto libre (nombre, posición, dorsal),
  sin exigir que cada uno tenga cuenta.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, stats
from app.deps import get_current_user, require_roles
from app.schemas import EquipoCreate, EquipoOut, EquipoUpdate, JugadorEquipoIn, JugadorEquipoOut

router = APIRouter()


# ---------------------------------------------------------------- helpers
def _out(eq: models.Equipo) -> EquipoOut:
    data = EquipoOut.model_validate(eq)
    data.jugadores = [JugadorEquipoOut.model_validate(j) for j in eq.jugadores]
    data.jugadores_count = len(eq.jugadores)
    return data


def _equipo_o_404(db: Session, equipo_id: int) -> models.Equipo:
    eq = db.get(models.Equipo, equipo_id)
    if eq is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return eq


def _verificar_dueno(eq: models.Equipo, usuario: models.Usuario):
    if usuario.rol.nombre != "superadmin" and eq.entrenador_id != usuario.id:
        raise HTTPException(status_code=403, detail="No es tu equipo")


def _sincronizar_plantilla(db: Session, eq: models.Equipo, jugadores: list[JugadorEquipoIn]):
    # Reemplaza por completo la plantilla del equipo
    for viejo in list(eq.jugadores):
        db.delete(viejo)
    db.flush()
    for j in jugadores:
        db.add(models.JugadorEquipo(equipo_id=eq.id, nombre=j.nombre, posicion=j.posicion, dorsal=j.dorsal))


# ---------------------------------------------------------------- listar
@router.get("", response_model=list[EquipoOut])
def listar_equipos(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    consulta = db.query(models.Equipo)
    if usuario.rol.nombre != "superadmin":
        consulta = consulta.filter(models.Equipo.entrenador_id == usuario.id)
    return [_out(e) for e in consulta.order_by(models.Equipo.id).all()]


# ---------------------------------------------------------------- resumen (home del entrenador)
@router.get("/resumen")
def resumen(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    equipos = db.query(models.Equipo).filter(models.Equipo.entrenador_id == usuario.id).order_by(models.Equipo.id).all()
    ids = [e.id for e in equipos]

    principal = None
    if equipos:
        e = equipos[0]
        torneos_activos = (
            db.query(models.Inscripcion)
            .join(models.Torneo, models.Inscripcion.torneo_id == models.Torneo.id)
            .filter(models.Inscripcion.equipo_id == e.id, models.Torneo.estado == "en_curso")
            .count()
        )
        principal = {
            "id": e.id, "nombre": e.nombre, "categoria": e.categoria,
            "jugadores": len(e.jugadores), "torneos_activos": torneos_activos,
        }

    proximo = None
    if ids:
        p = (
            db.query(models.Partido)
            .filter(
                or_(models.Partido.equipo_local_id.in_(ids), models.Partido.equipo_visitante_id.in_(ids)),
                models.Partido.estado.in_(["programado", "en_juego"]),
            )
            .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora)
            .first()
        )
        if p:
            propio = p.equipo_local_id in ids
            rival = p.equipo_visitante_nombre if propio else p.equipo_local_nombre
            proximo = {
                "id": p.id, "rival": rival, "fecha_hora": p.fecha_hora.isoformat() if p.fecha_hora else None,
                "torneo_nombre": p.torneo_nombre,
            }

    return {"equipos_count": len(equipos), "equipo_principal": principal, "proximo_partido": proximo}


# ---------------------------------------------------------------- próximos partidos del entrenador
@router.get("/mis-partidos")
def mis_partidos(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    ids = [e.id for e in db.query(models.Equipo).filter(models.Equipo.entrenador_id == usuario.id).all()]
    if not ids:
        return []
    partidos = (
        db.query(models.Partido)
        .filter(
            or_(models.Partido.equipo_local_id.in_(ids), models.Partido.equipo_visitante_id.in_(ids)),
            models.Partido.estado == "programado",
        )
        .order_by(models.Partido.fecha_hora.is_(None), models.Partido.fecha_hora)
        .all()
    )
    salida = []
    for p in partidos:
        mi_local = p.equipo_local_id in ids
        salida.append({
            "id": p.id,
            "mi_equipo_id": p.equipo_local_id if mi_local else p.equipo_visitante_id,
            "mi_equipo_nombre": p.equipo_local_nombre if mi_local else p.equipo_visitante_nombre,
            "rival_nombre": p.equipo_visitante_nombre if mi_local else p.equipo_local_nombre,
            "torneo_nombre": p.torneo_nombre,
            "fecha_hora": p.fecha_hora.isoformat() if p.fecha_hora else None,
            "estado": p.estado,
        })
    return salida


# ---------------------------------------------------------------- detalle
@router.get("/{equipo_id}", response_model=EquipoOut)
def ver_equipo(equipo_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)
    return _out(eq)
def ver_equipo(equipo_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)
    return _out(eq)


# ---------------------------------------------------------------- estadísticas del equipo
@router.get("/{equipo_id}/estadisticas")
def estadisticas_equipo(equipo_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)

    partidos = (
        db.query(models.Partido)
        .filter(or_(models.Partido.equipo_local_id == equipo_id, models.Partido.equipo_visitante_id == equipo_id))
        .all()
    )
    pj = pg = pe = pp = gf = gc = 0
    conteo_torneos: dict[int, int] = {}
    for p in partidos:
        if p.estado != "finalizado":
            continue
        local = p.equipo_local_id == equipo_id
        propios = p.goles_local if local else p.goles_visitante
        rivales = p.goles_visitante if local else p.goles_local
        pj += 1; gf += propios; gc += rivales
        if propios > rivales:
            pg += 1
        elif propios < rivales:
            pp += 1
        else:
            pe += 1
        conteo_torneos[p.torneo_id] = conteo_torneos.get(p.torneo_id, 0) + 1

    # Posición en la liga donde más ha jugado
    posicion = None
    torneo_nombre = None
    if conteo_torneos:
        torneo_id = max(conteo_torneos, key=conteo_torneos.get)
        tabla = stats.calcular_tabla(db, torneo_id)
        for i, fila in enumerate(tabla):
            if fila["equipo_id"] == equipo_id:
                posicion = i + 1
                break
        t = db.get(models.Torneo, torneo_id)
        torneo_nombre = t.nombre if t else None

    goleadores = []
    # Goleadores del equipo (eventos tipo gol con jugador identificado)
    from sqlalchemy import func
    filas = (
        db.query(models.Usuario.id, models.Usuario.nombre, func.count(models.EventoPartido.id).label("g"))
        .join(models.EventoPartido, models.EventoPartido.jugador_id == models.Usuario.id)
        .filter(models.EventoPartido.equipo_id == equipo_id, models.EventoPartido.tipo == "gol")
        .group_by(models.Usuario.id, models.Usuario.nombre)
        .order_by(func.count(models.EventoPartido.id).desc())
        .limit(10)
        .all()
    )
    goleadores = [{"jugador_id": f.id, "nombre": f.nombre, "goles": int(f.g)} for f in filas]

    return {
        "equipo": {"id": eq.id, "nombre": eq.nombre, "categoria": eq.categoria},
        "pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc,
        "posicion": posicion, "torneo_nombre": torneo_nombre,
        "goleadores": goleadores,
    }


# ---------------------------------------------------------------- crear
@router.post("", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(
    datos: EquipoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_roles("entrenador", "superadmin")),
):
    eq = models.Equipo(
        entrenador_id=usuario.id, nombre=datos.nombre,
        color=datos.color, categoria=datos.categoria, escudo_url=datos.escudo_url,
    )
    db.add(eq)
    db.flush()
    if datos.jugadores:
        _sincronizar_plantilla(db, eq, datos.jugadores)
    db.commit()
    db.refresh(eq)
    return _out(eq)


# ---------------------------------------------------------------- actualizar
@router.put("/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(
    equipo_id: int, datos: EquipoUpdate,
    db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user),
):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)

    for campo in ("nombre", "color", "categoria", "escudo_url"):
        valor = getattr(datos, campo)
        if valor is not None:
            setattr(eq, campo, valor)
    if datos.jugadores is not None:
        _sincronizar_plantilla(db, eq, datos.jugadores)

    db.commit()
    db.refresh(eq)
    return _out(eq)


# ---------------------------------------------------------------- borrar
@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_equipo(equipo_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)

    tiene_partidos = db.query(models.Partido).filter(
        or_(models.Partido.equipo_local_id == equipo_id, models.Partido.equipo_visitante_id == equipo_id)
    ).first()
    if tiene_partidos or eq.inscripciones:
        raise HTTPException(status_code=409, detail="No se puede borrar: el equipo tiene partidos o inscripciones")

    for j in list(eq.jugadores):
        db.delete(j)
    db.delete(eq)
    db.commit()


# ---------------------------------------------------------------- plantilla: agregar/quitar uno
@router.post("/{equipo_id}/jugadores", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def agregar_jugador(
    equipo_id: int, datos: JugadorEquipoIn,
    db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user),
):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)
    db.add(models.JugadorEquipo(equipo_id=eq.id, nombre=datos.nombre, posicion=datos.posicion, dorsal=datos.dorsal))
    db.commit()
    db.refresh(eq)
    return _out(eq)


@router.delete("/{equipo_id}/jugadores/{jugador_equipo_id}", response_model=EquipoOut)
def quitar_jugador(
    equipo_id: int, jugador_equipo_id: int,
    db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user),
):
    eq = _equipo_o_404(db, equipo_id)
    _verificar_dueno(eq, usuario)
    je = db.get(models.JugadorEquipo, jugador_equipo_id)
    if je is None or je.equipo_id != eq.id:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en la plantilla")
    db.delete(je)
    db.commit()
    db.refresh(eq)
    return _out(eq)
