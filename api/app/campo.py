"""
Quién está en el campo durante un partido.

    en_campo(equipo) = titulares del plan
                     − expulsados      (rojas > 0, directa o por doble amarilla)
                     − salidos         (salio == True)
                     + entrados        (entro == True)

Si el equipo NO registró plan, la plantilla entera cuenta como "en el campo"
(menos expulsados y salidos). No es una comodidad: sin plan el sistema no sabe
quién arrancó, y dejar al árbitro sin nadie elegible en mitad de un partido es
peor que no validar. Además es lo que sostiene los tests de eventos que ya
existen, que crean el partido sin registrar alineación. No lo quites.

Este módulo solo LEE: no hay tabla, columna ni migración nuevas.
"""
from sqlalchemy.orm import Session

from app import models
from app.eventos_resumen import resumen_por_jugador


def _plantilla_ids(db: Session, equipo_id: int) -> set[int]:
    """Ids de usuario de la plantilla del equipo."""
    equipo = db.get(models.Equipo, equipo_id)
    if equipo is None:
        return set()
    return {je.jugador_id for je in equipo.jugadores if je.jugador_id is not None}


def _plan_existe_y_titulares_ids(db: Session, partido_id: int, equipo_id: int) -> tuple[bool, set[int]]:
    """Devuelve (plan_existe, titulares_con_cuenta).
    plan_existe es True si el entrenador registró alineación.
    titulares_con_cuenta son los ids de usuario de los titulares (vacío si no hay plan o
    si los titulares carecen de cuenta registrada)."""
    plan = (
        db.query(models.AlineacionPlan)
        .filter_by(partido_id=partido_id, equipo_id=equipo_id)
        .first()
    )
    if plan is None:
        return False, set()
    titulares = {
        j.get("jugador_id")
        for j in (plan.jugadores or [])
        if j.get("jugador_id") is not None
    }
    return True, titulares


def estado_campo(db: Session, partido_id: int, equipo_id: int) -> dict:
    """
    Devuelve, para un equipo de un partido:

    - en_campo:   set[int]        ids de usuario que pueden recibir eventos
    - expulsados: set[int]        con al menos una roja
    - salidos:    set[int]        que salieron en un cambio
    - amarillas:  dict[int, int]  amarillas por jugador
    - hay_plan:   bool            False si el entrenador no registró alineación
    """
    resumen = resumen_por_jugador(db, partido_id)
    plantilla = _plantilla_ids(db, equipo_id)

    # El resumen es de TODO el partido; se acota a la plantilla del equipo.
    expulsados = {jid for jid, r in resumen.items() if r["rojas"] > 0} & plantilla
    salidos = {jid for jid, r in resumen.items() if r["salio"]} & plantilla
    entrados = {jid for jid, r in resumen.items() if r["entro"]} & plantilla

    hay_plan, titulares = _plan_existe_y_titulares_ids(db, partido_id, equipo_id)
    base = titulares if hay_plan else plantilla

    return {
        "en_campo": (base | entrados) - salidos - expulsados,
        "expulsados": expulsados,
        "salidos": salidos,
        "amarillas": {jid: r["amarillas"] for jid, r in resumen.items() if jid in plantilla},
        "hay_plan": hay_plan,
    }
