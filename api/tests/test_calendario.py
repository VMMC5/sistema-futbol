"""Generadores puros de calendario: liga (ida/vuelta) y eliminación (byes)."""
import random
from collections import Counter

from app import calendario


# ---------- normalizar_tipo ----------
def test_normalizar_tipo():
    assert calendario.normalizar_tipo("Liga") == "liga"
    assert calendario.normalizar_tipo("  Eliminación   Directa ") == "eliminacion directa"
    assert calendario.normalizar_tipo(None) is None
    assert calendario.normalizar_tipo("copa") == "copa"


# ---------- siguiente_potencia_de_2 ----------
def test_siguiente_potencia_de_2():
    assert calendario.siguiente_potencia_de_2(2) == 2
    assert calendario.siguiente_potencia_de_2(3) == 4
    assert calendario.siguiente_potencia_de_2(6) == 8
    assert calendario.siguiente_potencia_de_2(8) == 8


# ---------- liga ----------
def _pares(jornadas):
    return [frozenset(p) for j in jornadas for p in j]


def test_liga_par_ida_y_vuelta():
    jornadas = calendario.generar_liga([1, 2, 3, 4])
    assert len(jornadas) == 6                      # 2(n-1)
    assert all(len(j) == 2 for j in jornadas)      # n/2 partidos por jornada
    conteo = Counter(_pares(jornadas))
    assert len(conteo) == 6 and all(v == 2 for v in conteo.values())


def test_liga_localia_invertida_en_la_vuelta():
    jornadas = calendario.generar_liga([1, 2, 3, 4])
    ida, vuelta = jornadas[:3], jornadas[3:]
    partidos_ida = {p for j in ida for p in j}
    partidos_vuelta = {p for j in vuelta for p in j}
    assert partidos_vuelta == {(v, l) for (l, v) in partidos_ida}


def test_liga_impar_descansa():
    jornadas = calendario.generar_liga([1, 2, 3])
    assert len(jornadas) == 6                      # con fantasma: 2n
    assert all(len(j) == 1 for j in jornadas)      # uno descansa por jornada
    conteo = Counter(_pares(jornadas))
    assert len(conteo) == 3 and all(v == 2 for v in conteo.values())


def test_liga_nadie_juega_dos_veces_en_una_jornada():
    for j in calendario.generar_liga([1, 2, 3, 4, 5, 6]):
        vistos = [e for p in j for e in p]
        assert len(vistos) == len(set(vistos))


# ---------- eliminación ----------
def test_eliminacion_seis_equipos_dos_byes():
    byes, parejas = calendario.generar_ronda_eliminacion(
        [1, 2, 3, 4, 5, 6], random.Random(42))
    assert len(byes) == 2 and len(parejas) == 2
    usados = list(byes) + [e for p in parejas for e in p]
    assert sorted(usados) == [1, 2, 3, 4, 5, 6]    # todos, sin repetir


def test_eliminacion_potencia_exacta_sin_byes():
    byes, parejas = calendario.generar_ronda_eliminacion(
        [1, 2, 3, 4], random.Random(1))
    assert byes == [] and len(parejas) == 2


def test_eliminacion_dos_equipos_final_directa():
    byes, parejas = calendario.generar_ronda_eliminacion([1, 2], random.Random(1))
    assert byes == [] and len(parejas) == 1


def test_eliminacion_es_aleatoria_pero_reproducible():
    a = calendario.generar_ronda_eliminacion([1, 2, 3, 4, 5, 6], random.Random(7))
    b = calendario.generar_ronda_eliminacion([1, 2, 3, 4, 5, 6], random.Random(7))
    assert a == b
