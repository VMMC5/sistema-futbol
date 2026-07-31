"""
Partidos y eventos en vivo — módulo del árbitro.

Reglas de negocio destacadas:
- Solo el SUPERADMIN programa partidos (define torneo, equipos, cancha, árbitro).
- Solo el ÁRBITRO ASIGNADO (o el superadmin) puede iniciar/finalizar el partido
  y registrar eventos.
- Los eventos solo se registran mientras el partido está 'en_juego'.
- Al registrar un GOL, el marcador del equipo correspondiente se actualiza solo;
  al borrar un gol (corrección del árbitro), se descuenta.

Estados del partido:  programado -> en_juego -> finalizado
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import campo, eventos_resumen, models, notificaciones_service
from app.deps import es_admin, get_current_user, require_roles
from app.schemas import (
    AlineacionCreate,
    AlineacionOut,
    EventoCreate,
    EventoOut,
    PartidoCreate,
    PartidoOut,
    PartidoUpdate,
    PlanIn,
    PlanOut,
)

router = APIRouter()


def _ya_es_hora(fecha_hora) -> bool:
    """True si ya se llegó a la fecha/hora del partido (o si no tiene fecha)."""
    if fecha_hora is None:
        return True
    ahora = datetime.now(fecha_hora.tzinfo) if fecha_hora.tzinfo else datetime.now()
    return ahora >= fecha_hora


def _equipo_que_anota(partido, equipo_id, subtipo):
    """Equipo al que se le acredita un gol (un autogol cuenta para el rival)."""
    if subtipo == "autogol":
        return partido.equipo_visitante_id if equipo_id == partido.equipo_local_id else partido.equipo_local_id
    return equipo_id


# ---------- helpers ----------
def _obtener_partido(db: Session, partido_id: int) -> models.Partido:
    partido = db.get(models.Partido, partido_id)
    if partido is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return partido


def _puede_arbitrar(usuario: models.Usuario, partido: models.Partido) -> bool:
    """El superadmin siempre puede; un árbitro solo en SUS partidos asignados."""
    return es_admin(usuario) or usuario.id == partido.arbitro_id


def _exigir_arbitraje(usuario: models.Usuario, partido: models.Partido):
    if not _puede_arbitrar(usuario, partido):
        raise HTTPException(
            status_code=403,
            detail="Solo el árbitro asignado o un administrador puede gestionar este partido",
        )


def _avisar_partido(db, background_tasks, titulo: str, mensaje: str, usuario_ids) -> None:
    """Un aviso por usuario, sin repetir: el mismo entrenador puede dirigir a
    los dos equipos del partido. Los None se ignoran (partido sin árbitro)."""
    for uid in dict.fromkeys(u for u in usuario_ids if u):
        notificaciones_service.crear_notificacion(db, uid, titulo, mensaje, background_tasks)


# ======================================================================
#  Gestión del calendario (superadmin)
# ======================================================================
@router.post("", response_model=PartidoOut, status_code=status.HTTP_201_CREATED)
def crear_partido(
    datos: PartidoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    # Validar referencias
    if db.get(models.Torneo, datos.torneo_id) is None:
        raise HTTPException(status_code=400, detail="El torneo no existe")
    for eq_id in (datos.equipo_local_id, datos.equipo_visitante_id):
        if db.get(models.Equipo, eq_id) is None:
            raise HTTPException(status_code=400, detail=f"El equipo {eq_id} no existe")
    if datos.cancha_id and db.get(models.Cancha, datos.cancha_id) is None:
        raise HTTPException(status_code=400, detail="La cancha no existe")
    if datos.arbitro_id:
        arbitro = db.get(models.Usuario, datos.arbitro_id)
        if arbitro is None or arbitro.rol.nombre != "arbitro":
            raise HTTPException(status_code=400, detail="El árbitro indicado no es válido")

    partido = models.Partido(**datos.model_dump(), estado="programado")
    db.add(partido)
    db.commit()
    db.refresh(partido)

    # Avisos: al árbitro designado y a los entrenadores de ambos equipos.
    rivales = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
    cuando = f" el {partido.fecha_hora:%d/%m %H:%M}" if partido.fecha_hora else ""
    if partido.arbitro_id:
        _avisar_partido(db, background_tasks, "Partido asignado",
                        f"Pitarás {rivales}{cuando}.", [partido.arbitro_id])
    _avisar_partido(db, background_tasks, "Partido programado",
                    f"Tu equipo juega {rivales}{cuando}.",
                    [partido.equipo_local.entrenador_id, partido.equipo_visitante.entrenador_id])
    db.commit()
    return partido


@router.put("/{partido_id}", response_model=PartidoOut)
def actualizar_partido(
    partido_id: int,
    datos: PartidoUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    partido = _obtener_partido(db, partido_id)
    cambios = datos.model_dump(exclude_unset=True)
    # El loop de abajo es un setattr ciego: sin esta foto previa no hay forma
    # de saber qué cambió de verdad para avisar solo a quien corresponde.
    previo = {"arbitro_id": partido.arbitro_id, "fecha_hora": partido.fecha_hora,
              "cancha_id": partido.cancha_id}

    if "arbitro_id" in cambios and cambios["arbitro_id"] is not None:
        arbitro = db.get(models.Usuario, cambios["arbitro_id"])
        if arbitro is None or arbitro.rol.nombre != "arbitro":
            raise HTTPException(status_code=400, detail="El árbitro indicado no es válido")
    if "cancha_id" in cambios and cambios["cancha_id"] is not None:
        if db.get(models.Cancha, cambios["cancha_id"]) is None:
            raise HTTPException(status_code=400, detail="La cancha no existe")

    for campo, valor in cambios.items():
        setattr(partido, campo, valor)
    db.commit()
    db.refresh(partido)

    rivales = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
    cuando = f" el {partido.fecha_hora:%d/%m %H:%M}" if partido.fecha_hora else ""
    if "arbitro_id" in cambios and cambios["arbitro_id"] != previo["arbitro_id"]:
        _avisar_partido(db, background_tasks, "Partido asignado",
                        f"Pitarás {rivales}{cuando}.", [partido.arbitro_id])
        _avisar_partido(db, background_tasks, "Cambio de designación",
                        f"Ya no pitarás {rivales}.", [previo["arbitro_id"]])
    if (("fecha_hora" in cambios and cambios["fecha_hora"] != previo["fecha_hora"])
            or ("cancha_id" in cambios and cambios["cancha_id"] != previo["cancha_id"])):
        _avisar_partido(db, background_tasks, "Partido reprogramado",
                        f"{rivales}: nueva programación{cuando}.",
                        [partido.arbitro_id, partido.equipo_local.entrenador_id,
                         partido.equipo_visitante.entrenador_id])
    db.commit()
    return partido


@router.delete("/{partido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_partido(
    partido_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    partido = _obtener_partido(db, partido_id)
    db.delete(partido)
    db.commit()


# ======================================================================
#  Lectura (cualquier usuario autenticado)
# ======================================================================
@router.get("", response_model=list[PartidoOut])
def listar_partidos(
    torneo_id: int | None = None,
    estado: str | None = None,
    mios: bool = False,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Partido).options(*models.CARGA_PARTIDO)
    if mios:
        # Partidos asignados al árbitro autenticado (para el modo árbitro)
        consulta = consulta.filter(models.Partido.arbitro_id == usuario.id)
    if torneo_id:
        consulta = consulta.filter(models.Partido.torneo_id == torneo_id)
    if estado:
        consulta = consulta.filter(models.Partido.estado == estado)
    return consulta.order_by(models.Partido.id).all()


@router.get("/{partido_id}", response_model=PartidoOut)
def ver_partido(
    partido_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    return _obtener_partido(db, partido_id)


# ======================================================================
#  Acciones del árbitro en vivo
# ======================================================================
@router.post("/{partido_id}/iniciar", response_model=PartidoOut)
def iniciar_partido(
    partido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = _obtener_partido(db, partido_id)
    _exigir_arbitraje(usuario, partido)
    if partido.estado != "programado":
        raise HTTPException(status_code=409, detail="Solo se puede iniciar un partido programado")
    if not _ya_es_hora(partido.fecha_hora):
        raise HTTPException(status_code=409, detail="Aún no es la fecha y hora programadas del partido")

    partido.estado = "en_juego"
    db.commit()
    db.refresh(partido)
    return partido


@router.post("/{partido_id}/finalizar", response_model=PartidoOut)
def finalizar_partido(
    partido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = _obtener_partido(db, partido_id)
    _exigir_arbitraje(usuario, partido)
    if partido.estado != "en_juego":
        raise HTTPException(status_code=409, detail="Solo se puede finalizar un partido en juego")

    partido.estado = "finalizado"
    db.commit()
    db.refresh(partido)
    return partido


@router.post("/{partido_id}/acta", response_model=PartidoOut)
def firmar_acta(
    partido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """El árbitro firma digitalmente el acta y la envía al sistema."""
    partido = _obtener_partido(db, partido_id)
    _exigir_arbitraje(usuario, partido)
    if partido.estado != "finalizado":
        raise HTTPException(status_code=409, detail="El acta solo se firma cuando el partido ya finalizó")
    partido.acta_firmada = True
    partido.acta_firmada_en = datetime.now()
    db.commit()
    db.refresh(partido)
    return partido


@router.get("/{partido_id}/eventos", response_model=list[EventoOut])
def listar_eventos(
    partido_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    _obtener_partido(db, partido_id)  # 404 si no existe
    return (
        db.query(models.EventoPartido)
        .options(*models.CARGA_EVENTO)
        .filter(models.EventoPartido.partido_id == partido_id)
        .order_by(models.EventoPartido.minuto, models.EventoPartido.id)
        .all()
    )


@router.get("/{partido_id}/resumen-jugadores")
def resumen_jugadores(
    partido_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    _obtener_partido(db, partido_id)  # 404 si no existe
    return eventos_resumen.resumen_por_jugador(db, partido_id)


def _exigir_en_campo(estado: dict, jugador_id: int):
    """409 con el motivo concreto si el jugador no puede recibir eventos."""
    if jugador_id in estado["en_campo"]:
        return
    if jugador_id in estado["expulsados"]:
        raise HTTPException(status_code=409, detail="El jugador está expulsado")
    if jugador_id in estado["salidos"]:
        raise HTTPException(status_code=409, detail="El jugador ya salió de cambio")
    raise HTTPException(status_code=409, detail="El jugador no está en el campo")


def _validar_jugadores(estado: dict, datos: EventoCreate):
    """
    Un evento puede no llevar jugador y eso es legal: el autogol atribuido solo
    al equipo va sin jugador_id, y la asistencia de un gol es opcional. Cuando
    el campo viene vacío no hay nada que comprobar. Solo el cambio exige los dos.
    """
    if datos.tipo == "cambio":
        if datos.jugador_id is None or datos.jugador_secundario_id is None:
            raise HTTPException(
                status_code=409,
                detail="Un cambio necesita el jugador que sale y el que entra",
            )
        _exigir_en_campo(estado, datos.jugador_id)          # el que sale
        entra = datos.jugador_secundario_id
        if entra in estado["expulsados"]:
            raise HTTPException(status_code=409, detail="El jugador que entra está expulsado")
        # Un jugador que ya salió de cambio no puede volver a entrar: el fútbol
        # no permite reingresos, y además dejaría a DOS jugadores fuera del
        # campo sin forma de recibir eventos (el que ya salió y el que "entraría" en su lugar).
        if entra in estado["salidos"]:
            raise HTTPException(status_code=409, detail="El jugador ya salió de cambio y no puede volver a entrar")
        # Sin plan, la plantilla entera cuenta como "en el campo", así que esta
        # comprobación no se puede aplicar: dejaría todo cambio en 409.
        if estado["hay_plan"] and entra in estado["en_campo"]:
            raise HTTPException(status_code=409, detail="El jugador que entra ya está en el campo")
        return

    if datos.jugador_id is not None:
        _exigir_en_campo(estado, datos.jugador_id)
    if datos.tipo == "gol" and datos.jugador_secundario_id is not None:
        _exigir_en_campo(estado, datos.jugador_secundario_id)   # asistente


@router.post("/{partido_id}/eventos", response_model=EventoOut, status_code=status.HTTP_201_CREATED)
def registrar_evento(
    partido_id: int,
    datos: EventoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = _obtener_partido(db, partido_id)
    _exigir_arbitraje(usuario, partido)

    if partido.estado != "en_juego":
        raise HTTPException(
            status_code=409,
            detail="Solo se pueden registrar eventos mientras el partido está en juego",
        )

    # El equipo del evento debe ser uno de los dos que disputan el partido
    if datos.equipo_id not in (partido.equipo_local_id, partido.equipo_visitante_id):
        raise HTTPException(status_code=400, detail="El equipo no participa en este partido")

    estado = campo.estado_campo(db, partido_id, datos.equipo_id)
    _validar_jugadores(estado, datos)

    evento = models.EventoPartido(
        partido_id=partido_id,
        equipo_id=datos.equipo_id,
        jugador_id=datos.jugador_id,
        jugador_secundario_id=datos.jugador_secundario_id,
        tipo=datos.tipo,
        subtipo=datos.subtipo if datos.tipo == "gol" else None,
        minuto=datos.minuto,
        detalle=datos.detalle,
    )
    db.add(evento)

    # Segunda amarilla = expulsión. Se crea un evento de roja APARTE porque los
    # distintivos, el acta y las estadísticas ya cuentan rojas leyendo eventos:
    # marcar la amarilla obligaría a cambiar los cuatro consumidores.
    # `estado` se calculó antes de añadir esta amarilla, así que cuenta las previas.
    if (
        datos.tipo == "tarjeta_amarilla"
        and datos.jugador_id is not None
        and estado["amarillas"].get(datos.jugador_id, 0) >= 1
    ):
        db.add(models.EventoPartido(
            partido_id=partido_id,
            equipo_id=datos.equipo_id,
            jugador_id=datos.jugador_id,
            tipo="tarjeta_roja",
            minuto=datos.minuto,
            detalle="Doble amarilla",
        ))

    # Si es gol, actualizar el marcador. Un autogol cuenta para el rival.
    if datos.tipo == "gol":
        anota = _equipo_que_anota(partido, datos.equipo_id, datos.subtipo)
        if anota == partido.equipo_local_id:
            partido.goles_local += 1
        else:
            partido.goles_visitante += 1

    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/{partido_id}/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_evento(
    partido_id: int,
    evento_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Corrección del árbitro: borra un evento y, si era gol, descuenta el marcador."""
    partido = _obtener_partido(db, partido_id)
    _exigir_arbitraje(usuario, partido)

    evento = db.get(models.EventoPartido, evento_id)
    if evento is None or evento.partido_id != partido_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado en este partido")

    if evento.tipo == "gol":
        anota = _equipo_que_anota(partido, evento.equipo_id, evento.subtipo)
        if anota == partido.equipo_local_id and partido.goles_local > 0:
            partido.goles_local -= 1
        elif anota == partido.equipo_visitante_id and partido.goles_visitante > 0:
            partido.goles_visitante -= 1

    # Si se borra una amarilla y al jugador le quedan menos de dos, la roja
    # automática de la doble amarilla (si la hay) queda huérfana: sin esto el
    # jugador seguiría expulsado sin tener la segunda amarilla que lo justifique.
    # No toca una roja directa: esa no tiene el detalle "Doble amarilla".
    if evento.tipo == "tarjeta_amarilla" and evento.jugador_id is not None:
        amarillas_restantes = (
            db.query(models.EventoPartido)
            .filter(
                models.EventoPartido.partido_id == partido_id,
                models.EventoPartido.tipo == "tarjeta_amarilla",
                models.EventoPartido.jugador_id == evento.jugador_id,
                models.EventoPartido.id != evento.id,
            )
            .count()
        )
        if amarillas_restantes < 2:
            roja_automatica = (
                db.query(models.EventoPartido)
                .filter(
                    models.EventoPartido.partido_id == partido_id,
                    models.EventoPartido.tipo == "tarjeta_roja",
                    models.EventoPartido.jugador_id == evento.jugador_id,
                    models.EventoPartido.detalle == "Doble amarilla",
                )
                .first()
            )
            if roja_automatica is not None:
                db.delete(roja_automatica)

    db.delete(evento)
    db.commit()


# ======================================================================
#  Alineaciones (las define el entrenador del equipo, antes del partido)
# ======================================================================
def _puede_gestionar_alineacion(usuario: models.Usuario, equipo: models.Equipo) -> bool:
    """El superadmin siempre; un entrenador solo la de SU equipo."""
    return es_admin(usuario) or usuario.id == equipo.entrenador_id


@router.get("/{partido_id}/alineacion", response_model=list[AlineacionOut])
def listar_alineacion(
    partido_id: int,
    equipo_id: int | None = None,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    _obtener_partido(db, partido_id)  # 404 si no existe
    consulta = (
        db.query(models.Alineacion)
        .options(*models.CARGA_ALINEACION)
        .filter(models.Alineacion.partido_id == partido_id)
    )
    if equipo_id:
        consulta = consulta.filter(models.Alineacion.equipo_id == equipo_id)
    return consulta.order_by(models.Alineacion.equipo_id, models.Alineacion.id).all()


@router.post("/{partido_id}/alineacion", response_model=AlineacionOut, status_code=status.HTTP_201_CREATED)
def agregar_a_alineacion(
    partido_id: int,
    datos: AlineacionCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = _obtener_partido(db, partido_id)

    # La alineacion se arma ANTES de que arranque el partido
    if partido.estado != "programado":
        raise HTTPException(
            status_code=409,
            detail="La alineación solo se puede modificar antes de iniciar el partido",
        )

    # El equipo debe disputar este partido
    if datos.equipo_id not in (partido.equipo_local_id, partido.equipo_visitante_id):
        raise HTTPException(status_code=400, detail="El equipo no participa en este partido")

    equipo = db.get(models.Equipo, datos.equipo_id)
    if equipo is None:
        raise HTTPException(status_code=400, detail="El equipo no existe")

    # Solo el entrenador de ESE equipo (o el admin) arma su alineacion
    if not _puede_gestionar_alineacion(usuario, equipo):
        raise HTTPException(
            status_code=403,
            detail="Solo el entrenador del equipo o un administrador puede modificar la alineación",
        )

    # El jugador debe pertenecer al equipo (estar en jugadores_equipo)
    pertenece = (
        db.query(models.JugadorEquipo)
        .filter_by(equipo_id=datos.equipo_id, jugador_id=datos.jugador_id)
        .first()
    )
    if pertenece is None:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a ese equipo")

    # No repetir al jugador en la alineacion del mismo partido
    ya_alineado = (
        db.query(models.Alineacion)
        .filter_by(partido_id=partido_id, jugador_id=datos.jugador_id)
        .first()
    )
    if ya_alineado is not None:
        raise HTTPException(status_code=409, detail="El jugador ya está en la alineación")

    alineacion = models.Alineacion(
        partido_id=partido_id,
        equipo_id=datos.equipo_id,
        jugador_id=datos.jugador_id,
        titular=datos.titular,
        posicion=datos.posicion,
    )
    db.add(alineacion)
    db.commit()
    db.refresh(alineacion)
    return alineacion


@router.delete("/{partido_id}/alineacion/{alineacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_de_alineacion(
    partido_id: int,
    alineacion_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = _obtener_partido(db, partido_id)
    if partido.estado != "programado":
        raise HTTPException(
            status_code=409,
            detail="La alineación solo se puede modificar antes de iniciar el partido",
        )

    alineacion = db.get(models.Alineacion, alineacion_id)
    if alineacion is None or alineacion.partido_id != partido_id:
        raise HTTPException(status_code=404, detail="Alineación no encontrada en este partido")

    equipo = db.get(models.Equipo, alineacion.equipo_id)
    if not _puede_gestionar_alineacion(usuario, equipo):
        raise HTTPException(
            status_code=403,
            detail="Solo el entrenador del equipo o un administrador puede modificar la alineación",
        )

    db.delete(alineacion)
    db.commit()


# ======================================================================
#  PLAN DE ALINEACIÓN (formación del entrenador) — independiente del árbitro
# ======================================================================
def _plan_a_salida(db: Session, partido_id: int, equipo_id: int, plan: models.AlineacionPlan | None) -> PlanOut:
    titulares = plan.jugadores if plan else []
    titulares_ids = {j.get("jugador_equipo_id") for j in titulares}
    # Banca: jugadores de la plantilla que no están en la alineación titular
    equipo = db.get(models.Equipo, equipo_id)
    suplentes = []
    if equipo:
        for je in equipo.jugadores:
            if je.id not in titulares_ids:
                suplentes.append({
                    "jugador_equipo_id": je.id,
                    "jugador_id": je.jugador_id,
                    "nombre": je.nombre_jugador,
                    "dorsal": je.dorsal,
                    "posicion": je.posicion,
                    "orden": -1,
                })

    # tiene_foto por jugador, en UNA sola consulta para todo el plan (el panel web
    # solo pinta el <img> cuando es True, así evita imágenes rotas para los que no
    # tienen foto). No se mutan los dicts persistidos: se construyen copias.
    ids = {j.get("jugador_id") for j in titulares if j.get("jugador_id")}
    ids |= {s["jugador_id"] for s in suplentes if s["jugador_id"]}
    con_foto = set()
    if ids:
        con_foto = {
            uid for (uid,) in db.query(models.Usuario.id)
            .filter(models.Usuario.id.in_(ids), models.Usuario.foto_nombre.isnot(None))
            .all()
        }

    estado = campo.estado_campo(db, partido_id, equipo_id)

    def _enriquecer(d):
        jid = d.get("jugador_id")
        return {
            **d,
            "tiene_foto": jid in con_foto,
            "en_campo": jid is not None and jid in estado["en_campo"],
            "expulsado": jid is not None and jid in estado["expulsados"],
        }

    return PlanOut(
        partido_id=partido_id,
        equipo_id=equipo_id,
        formacion=plan.formacion if plan else "4-4-2",
        jugadores=[_enriquecer(j) for j in titulares],
        suplentes=[_enriquecer(s) for s in suplentes],
    )


@router.get("/{partido_id}/plan", response_model=PlanOut)
def ver_plan(
    partido_id: int,
    equipo_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = db.get(models.Partido, partido_id)
    if partido is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    if equipo_id not in (partido.equipo_local_id, partido.equipo_visitante_id):
        raise HTTPException(status_code=400, detail="El equipo no juega este partido")

    equipo = db.get(models.Equipo, equipo_id)
    # Puede ver el plan: el entrenador dueño, el admin, o el árbitro asignado al partido
    es_arbitro = partido.arbitro_id == usuario.id
    if not (_puede_gestionar_alineacion(usuario, equipo) or es_arbitro):
        raise HTTPException(status_code=403, detail="No puedes ver la alineación de este equipo")

    plan = (
        db.query(models.AlineacionPlan)
        .filter_by(partido_id=partido_id, equipo_id=equipo_id)
        .first()
    )
    return _plan_a_salida(db, partido_id, equipo_id, plan)


@router.put("/{partido_id}/plan", response_model=PlanOut)
def guardar_plan(
    partido_id: int,
    datos: PlanIn,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    partido = db.get(models.Partido, partido_id)
    if partido is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    if datos.equipo_id not in (partido.equipo_local_id, partido.equipo_visitante_id):
        raise HTTPException(status_code=400, detail="El equipo no juega este partido")
    if partido.estado != "programado":
        raise HTTPException(status_code=409, detail="La alineación solo se edita antes de iniciar el partido")

    equipo = db.get(models.Equipo, datos.equipo_id)
    if not _puede_gestionar_alineacion(usuario, equipo):
        raise HTTPException(status_code=403, detail="No es tu equipo")

    # Una alineación sin nadie no es una alineación. Guardarla dejaba al partido
    # sin plan y al entrenador creyendo que lo había confirmado.
    if not datos.jugadores:
        raise HTTPException(
            status_code=400,
            detail="La alineación debe tener al menos un jugador",
        )

    # Resolver cada hueco contra la plantilla del equipo (y tomar nombre/dorsal)
    plantilla = {j.id: j for j in equipo.jugadores}
    items = []
    vistos = set()
    for it in datos.jugadores:
        je = plantilla.get(it.jugador_equipo_id)
        if je is None:
            raise HTTPException(status_code=400, detail="Un jugador no pertenece a la plantilla del equipo")
        if je.id in vistos:
            raise HTTPException(status_code=400, detail="Un jugador está repetido en la alineación")
        vistos.add(je.id)
        items.append({
            "jugador_equipo_id": je.id,
            "jugador_id": je.jugador_id,
            "nombre": je.nombre_jugador,
            "dorsal": je.dorsal,
            "posicion": it.posicion,
            "orden": it.orden,
        })

    plan = (
        db.query(models.AlineacionPlan)
        .filter_by(partido_id=partido_id, equipo_id=datos.equipo_id)
        .first()
    )
    if plan is None:
        plan = models.AlineacionPlan(partido_id=partido_id, equipo_id=datos.equipo_id)
        db.add(plan)
    plan.formacion = datos.formacion
    plan.jugadores = items
    db.commit()
    db.refresh(plan)
    return _plan_a_salida(db, partido_id, datos.equipo_id, plan)
