"""
CRUD de Torneos — primera rebanada vertical completa.

Sirve de PLANTILLA para los demás módulos (reservas, equipos, partidos):
muestra el patrón de listar/ver (cualquier usuario autenticado) y
crear/editar/eliminar (solo superadmin).

Reglas de acceso:
- Consultar (GET): cualquier usuario autenticado.
- Crear/editar/eliminar: solo 'superadmin'.
"""
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, notificaciones_service, calendario
from app.deps import get_current_user, require_roles
from app.schemas import TorneoCreate, TorneoOut, TorneoUpdate, TorneoIniciar, TorneoSiguienteRonda

router = APIRouter()


def _obtener_torneo(db: Session, torneo_id: int) -> models.Torneo:
    torneo = db.get(models.Torneo, torneo_id)
    if torneo is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return torneo


# ---------- Lectura (cualquier usuario autenticado) ----------
@router.get("", response_model=list[TorneoOut])
def listar_torneos(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Torneo)
    if estado:
        consulta = consulta.filter(models.Torneo.estado == estado)
    return consulta.order_by(models.Torneo.id).all()


@router.get("/{torneo_id}", response_model=TorneoOut)
def ver_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    return _obtener_torneo(db, torneo_id)


# ---------- Escritura (solo superadmin) ----------
@router.post("", response_model=TorneoOut, status_code=status.HTTP_201_CREATED)
def crear_torneo(
    datos: TorneoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    # La sede referenciada debe existir
    if db.get(models.Sede, datos.sede_id) is None:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")

    torneo = models.Torneo(**datos.model_dump())
    db.add(torneo)
    db.commit()
    db.refresh(torneo)

    # Aviso a TODOS los entrenadores: un torneo no pertenece a nadie hasta que
    # hay inscripciones, así que no existe otra audiencia posible.
    cierre = (f" Inscripciones hasta el {torneo.fecha_cierre_inscripciones:%d/%m/%Y}."
              if torneo.fecha_cierre_inscripciones else "")
    entrenadores = (
        db.query(models.Usuario.id)
        .join(models.Rol, models.Usuario.rol_id == models.Rol.id)
        .filter(models.Rol.nombre == "entrenador")
        .all()
    )
    for (uid,) in entrenadores:
        notificaciones_service.crear_notificacion(
            db, uid, "Torneo nuevo", f"Ya abrió {torneo.nombre}.{cierre}", background_tasks)
    db.commit()
    return torneo


@router.put("/{torneo_id}", response_model=TorneoOut)
def actualizar_torneo(
    torneo_id: int,
    datos: TorneoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)

    cambios = datos.model_dump(exclude_unset=True)  # solo lo que se envió
    if "sede_id" in cambios and db.get(models.Sede, cambios["sede_id"]) is None:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")

    for campo, valor in cambios.items():
        setattr(torneo, campo, valor)

    db.commit()
    db.refresh(torneo)
    return torneo


@router.delete("/{torneo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    db.delete(torneo)
    db.commit()
    # 204: sin cuerpo de respuesta


TIPOS_INICIABLES = ("liga", "eliminacion directa")


def _canchas_de_la_sede(db: Session, torneo: models.Torneo) -> list[int]:
    return [c.id for c in (db.query(models.Cancha)
                           .filter_by(sede_id=torneo.sede_id)
                           .order_by(models.Cancha.id).all())]


def _crear_partidos(db, torneo, jornadas, base, canchas, primera_jornada=1):
    """Inserta las jornadas; semanas consecutivas, +2h por partido de jornada."""
    creados = 0
    for nj, jornada in enumerate(jornadas):
        for np_, (local, visita) in enumerate(jornada):
            db.add(models.Partido(
                torneo_id=torneo.id,
                equipo_local_id=local, equipo_visitante_id=visita,
                cancha_id=canchas[creados % len(canchas)] if canchas else None,
                fecha_hora=base + timedelta(weeks=nj, hours=2 * np_),
                estado="programado", jornada=primera_jornada + nj,
            ))
            creados += 1
    return creados


@router.post("/{torneo_id}/iniciar")
def iniciar_torneo(
    torneo_id: int,
    datos: TorneoIniciar,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    if torneo.estado != "programado":
        raise HTTPException(status_code=409, detail="Solo se puede iniciar un torneo programado")
    tipo = calendario.normalizar_tipo(torneo.tipo)
    if tipo not in TIPOS_INICIABLES:
        raise HTTPException(
            status_code=400,
            detail="El tipo del torneo debe ser 'liga' o 'eliminación directa'")
    inscripciones = (db.query(models.Inscripcion)
                     .filter_by(torneo_id=torneo.id, estado="aceptada").all())
    equipos = [i.equipo_id for i in inscripciones]
    if len(equipos) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se necesitan al menos 2 equipos con inscripción aceptada")

    base = datetime.combine(datos.primera_fecha, datos.hora_base, tzinfo=timezone.utc)
    if tipo == "liga":
        jornadas = calendario.generar_liga(equipos)
    else:
        # Los byes no se guardan: se derivan (aceptados que no juegan la ronda 1).
        _byes, parejas = calendario.generar_ronda_eliminacion(equipos, random.Random())
        jornadas = [parejas]

    creados = _crear_partidos(db, torneo, jornadas, base, _canchas_de_la_sede(db, torneo))
    torneo.estado = "en_curso"
    db.commit()

    # UNA notificación por entrenador (no por partido: serían cientos).
    entrenadores = {db.get(models.Equipo, eid).entrenador_id for eid in equipos}
    for uid in entrenadores:
        notificaciones_service.crear_notificacion(
            db, uid, "Torneo iniciado",
            f"{torneo.nombre} comenzó: revisa tu calendario.", background_tasks)
    db.commit()
    return {"torneo_id": torneo.id, "estado": torneo.estado, "partidos_creados": creados}


@router.post("/{torneo_id}/siguiente-ronda")
def siguiente_ronda(
    torneo_id: int,
    datos: TorneoSiguienteRonda,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    if calendario.normalizar_tipo(torneo.tipo) != "eliminacion directa":
        raise HTTPException(status_code=400,
                            detail="Solo aplica a torneos de eliminación directa")
    if torneo.estado != "en_curso":
        raise HTTPException(status_code=409, detail="El torneo no está en curso")

    partidos = db.query(models.Partido).filter_by(torneo_id=torneo.id).all()
    ronda_actual = max((p.jornada or 0) for p in partidos)
    de_ronda = [p for p in partidos if (p.jornada or 0) == ronda_actual]
    pendientes = [p for p in de_ronda if p.estado != "finalizado"]
    if pendientes:
        raise HTTPException(
            status_code=409,
            detail=f"Faltan {len(pendientes)} partidos de la ronda {ronda_actual} por finalizar")

    # El empate es imposible en eliminación (lo bloquea /finalizar).
    ganadores = [p.equipo_local_id if p.goles_local > p.goles_visitante
                 else p.equipo_visitante_id for p in de_ronda]
    if ronda_actual == 1:
        # Byes derivados: aceptados que no jugaron la ronda 1.
        jugaron = ({p.equipo_local_id for p in de_ronda}
                   | {p.equipo_visitante_id for p in de_ronda})
        aceptados = [i.equipo_id for i in
                     db.query(models.Inscripcion)
                     .filter_by(torneo_id=torneo.id, estado="aceptada").all()]
        ganadores += [e for e in aceptados if e not in jugaron]

    if len(ganadores) == 1:
        torneo.estado = "finalizado"
        db.commit()
        campeon = db.get(models.Equipo, ganadores[0])
        return {"campeon_id": campeon.id, "campeon": campeon.nombre,
                "estado": "finalizado", "partidos_creados": 0}

    # ganadores + byes suman potencia de 2 -> aquí ya no hay byes nuevos.
    _byes, parejas = calendario.generar_ronda_eliminacion(ganadores, random.Random())
    base = datetime.combine(datos.fecha, datos.hora_base, tzinfo=timezone.utc)
    creados = _crear_partidos(db, torneo, [parejas], base,
                              _canchas_de_la_sede(db, torneo),
                              primera_jornada=ronda_actual + 1)
    db.commit()
    return {"ronda": ronda_actual + 1, "partidos_creados": creados,
            "estado": torneo.estado}
