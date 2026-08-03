"""Pruebas del builder del bracket (construir_llaves).

Los partidos entran como los devuelve GET /partidos?torneo_id= (dicts del
JSON de la API). El builder reconstruye el árbol hacia atrás desde la ronda
más alta porque el sistema re-sortea cada ronda.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llaves import construir_llaves  # noqa: E402


def _p(jornada, loc, vis, gl=None, gv=None, pid=None):
    """Partido en el formato del JSON de la API (solo los campos que se usan)."""
    finalizado = gl is not None
    return {
        "id": pid or (jornada * 100 + loc),
        "jornada": jornada,
        "equipo_local_id": loc, "equipo_local_nombre": f"Equipo {loc}",
        "equipo_visitante_id": vis, "equipo_visitante_nombre": f"Equipo {vis}",
        "goles_local": gl or 0, "goles_visitante": gv or 0,
        "estado": "finalizado" if finalizado else "programado",
        "fecha_hora": "2026-07-11T16:00:00Z",
    }


def _equipos_de(slot):
    return (slot["local"], slot["visitante"])


def test_ocho_equipos_completo():
    """Bracket clásico: 4 cuartos, 2 semis, final jugada. 2 columnas por lado."""
    partidos = [
        _p(1, 1, 2, 2, 0), _p(1, 3, 4, 1, 3), _p(1, 5, 6, 0, 1), _p(1, 7, 8, 2, 1),
        _p(2, 1, 4, 1, 0), _p(2, 6, 7, 0, 2),   # ganadores: 1, 7
        _p(3, 1, 7, 3, 1),                        # campeón: 1
    ]
    b = construir_llaves(partidos)
    assert b["final"]["tipo"] == "partido" and b["campeon"] == "Equipo 1"
    izq, der = b["lados"]["izquierda"], b["lados"]["derecha"]
    # cada lado: columna de ronda 1 (2 slots) y de ronda 2 (1 slot)
    assert [c["titulo"] for c in izq] == ["Cuartos de final", "Semifinales"]
    assert len(izq[0]["slots"]) == 2 and len(izq[1]["slots"]) == 1
    assert len(der[0]["slots"]) == 2 and len(der[1]["slots"]) == 1
    # adyacencia: los alimentadores de la semifinal izquierda son exactamente
    # los dos partidos de su columna de ronda 1
    semi_izq = izq[1]["slots"][0]
    alimentadores = {_equipos_de(s) for s in izq[0]["slots"]}
    assert all(e in {eq for par in alimentadores for eq in par}
               for e in _equipos_de(semi_izq))
    # ganador en el slot
    assert b["final"]["ganador"] == "local"


def test_seis_equipos_con_byes():
    """6 equipos: ronda 1 con 2 partidos y 2 byes; los byes son hojas."""
    partidos = [
        _p(1, 3, 4, 2, 1), _p(1, 5, 6, 0, 2),     # ganadores 3 y 6; byes: 1 y 2
        _p(2, 1, 3, 1, 2), _p(2, 2, 6, 3, 0),     # ganadores 3 y 2
        _p(3, 3, 2, 2, 0),                         # campeón 3
    ]
    b = construir_llaves(partidos)
    assert b["campeon"] == "Equipo 3"
    todos = [s for lado in b["lados"].values() for c in lado for s in c["slots"]]
    byes = [s for s in todos if s["tipo"] == "bye"]
    assert sorted(s["nombre"] for s in byes) == ["Equipo 1", "Equipo 2"]
    # los byes viven en columnas tituladas como la ronda 1 (Cuartos: 2 partidos + 2 byes)
    for lado in b["lados"].values():
        assert len(lado) == 2  # ronda 1 y semifinales


def test_parcial_solo_ronda_uno():
    """8 equipos, solo la ronda 1 jugándose: sin final, mitades 2/2."""
    partidos = [_p(1, 1, 2), _p(1, 3, 4), _p(1, 5, 6), _p(1, 7, 8)]
    b = construir_llaves(partidos)
    assert b["final"] is None and b["campeon"] is None
    assert len(b["lados"]["izquierda"]) == 1 and len(b["lados"]["derecha"]) == 1
    assert len(b["lados"]["izquierda"][0]["slots"]) == 2
    assert len(b["lados"]["derecha"][0]["slots"]) == 2


def test_dos_equipos_solo_final():
    b = construir_llaves([_p(1, 1, 2, 1, 0)])
    assert b["final"]["tipo"] == "partido" and b["campeon"] == "Equipo 1"
    assert b["lados"]["izquierda"] == [] and b["lados"]["derecha"] == []


def test_final_sin_jugar_no_tiene_campeon():
    partidos = [_p(1, 1, 2, 2, 0), _p(1, 3, 4, 0, 1), _p(2, 1, 4)]
    b = construir_llaves(partidos)
    assert b["final"]["tipo"] == "partido" and b["campeon"] is None
    assert b["final"]["ganador"] is None


def test_sin_partidos():
    assert construir_llaves([]) is None
    assert construir_llaves([{"jornada": None}]) is None
