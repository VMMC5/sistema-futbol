"""
Resumen de eventos por jugador de un partido.

Deriva de los EventoPartido lo necesario para los distintivos de la alineación:
goles, asistencias, tarjetas y si el jugador entró o salió. No toca el modelo;
solo lee y agrega.
"""
from sqlalchemy.orm import Session

from app import models


def _vacio() -> dict:
    return {"goles": 0, "asistencias": 0, "amarillas": 0, "rojas": 0,
            "salio": False, "entro": False}


def resumen_por_jugador(db: Session, partido_id: int) -> dict[int, dict]:
    eventos = (
        db.query(models.EventoPartido)
        .filter(models.EventoPartido.partido_id == partido_id)
        .all()
    )
    res: dict[int, dict] = {}

    def slot(jid: int) -> dict:
        return res.setdefault(jid, _vacio())

    for e in eventos:
        if e.tipo == "gol":
            # Un autogol no se le acredita al que lo marca (coherente con
            # _equipo_que_anota en routers/partidos.py).
            if e.subtipo != "autogol" and e.jugador_id is not None:
                slot(e.jugador_id)["goles"] += 1
            if e.jugador_secundario_id is not None:
                slot(e.jugador_secundario_id)["asistencias"] += 1
        elif e.tipo == "tarjeta_amarilla" and e.jugador_id is not None:
            slot(e.jugador_id)["amarillas"] += 1
        elif e.tipo == "tarjeta_roja" and e.jugador_id is not None:
            slot(e.jugador_id)["rojas"] += 1
        elif e.tipo == "cambio":
            if e.jugador_id is not None:
                slot(e.jugador_id)["salio"] = True
            if e.jugador_secundario_id is not None:
                slot(e.jugador_secundario_id)["entro"] = True

    return res
