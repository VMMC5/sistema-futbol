"""Reconstrucción del bracket de un torneo de eliminación directa.

El sistema RE-SORTEA cada ronda (decisión del spec de iniciar-torneo), así que
aquí no hay llave fija que leer: el árbol se reconstruye HACIA ATRÁS desde la
ronda más alta — el alimentador de un participante es el partido de la ronda
anterior donde jugó. Si no existe, el equipo entró por bye (pase directo) y se
pinta como hoja; por invariante del sistema eso solo pasa de la ronda 1 a la 2,
pero si datos manuales lo violan la hoja se pinta igual donde caiga.

La estructura de salida está pensada para Jinja sin recursión: columnas por
lado (ronda 1 -> cercana al centro), la final al centro y el campeón aparte.
"""
import math


def _nombre_ronda(distancia_a_la_final):
    return {0: "Final", 1: "Semifinales", 2: "Cuartos de final",
            3: "Octavos de final"}.get(distancia_a_la_final,
                                       f"Ronda de {2 ** (distancia_a_la_final + 1)}")


def _slot(p):
    ganador = None
    if p.get("estado") == "finalizado":
        if p["goles_local"] > p["goles_visitante"]:
            ganador = "local"
        elif p["goles_visitante"] > p["goles_local"]:
            ganador = "visitante"
    return {
        "tipo": "partido",
        "fecha": (p.get("fecha_hora") or "")[:10],
        "local": p.get("equipo_local_nombre") or f"Equipo {p.get('equipo_local_id')}",
        "visitante": p.get("equipo_visitante_nombre") or f"Equipo {p.get('equipo_visitante_id')}",
        "gl": p.get("goles_local", 0), "gv": p.get("goles_visitante", 0),
        "estado": p.get("estado"),
        "ganador": ganador,
    }


def construir_llaves(partidos):
    """partidos: dicts del JSON de GET /partidos?torneo_id=. None si no hay
    calendario de eliminación (ningún partido con jornada)."""
    elim = [p for p in partidos if p.get("jornada")]
    if not elim:
        return None

    rondas = {}
    for p in elim:
        rondas.setdefault(p["jornada"], []).append(p)
    for r in rondas:
        rondas[r].sort(key=lambda p: p.get("id", 0))
    k = max(rondas)

    indice = {}
    for r, ps in rondas.items():
        for p in ps:
            indice[(r, p.get("equipo_local_id"))] = p
            indice[(r, p.get("equipo_visitante_id"))] = p

    def niveles_alimentadores(equipo_id, nombre, ronda):
        """Niveles bajo un participante de `ronda`: niveles[0] = ronda-1, etc."""
        if ronda <= 1:
            return []
        alimentador = indice.get((ronda - 1, equipo_id))
        if alimentador is None:
            return [[{"tipo": "bye", "nombre": nombre}]]
        niveles = [[_slot(alimentador)]]
        izq = niveles_alimentadores(alimentador.get("equipo_local_id"),
                                    alimentador.get("equipo_local_nombre"),
                                    ronda - 1)
        der = niveles_alimentadores(alimentador.get("equipo_visitante_id"),
                                    alimentador.get("equipo_visitante_nombre"),
                                    ronda - 1)
        for j in range(max(len(izq), len(der))):
            a = izq[j] if j < len(izq) else []
            b = der[j] if j < len(der) else []
            niveles.append(a + b)
        return niveles

    raices = rondas[k]
    final = campeon = None

    if len(raices) == 1:
        p_final = raices[0]
        final = _slot(p_final)
        if final["ganador"]:
            campeon = final["local"] if final["ganador"] == "local" else final["visitante"]
        niveles_izq = niveles_alimentadores(
            p_final.get("equipo_local_id"), p_final.get("equipo_local_nombre"), k)
        niveles_der = niveles_alimentadores(
            p_final.get("equipo_visitante_id"), p_final.get("equipo_visitante_nombre"), k)
        ronda_de_nivel = lambda j: k - 1 - j          # nivel 0 = ronda k-1
        k_virtual = k
    else:
        # Torneo a medias: la ronda más alta aún tiene varios partidos. Se
        # reparten los subárboles mitad y mitad y el centro queda "por definir".
        mitad = math.ceil(len(raices) / 2)

        def lado_de(raices_lado):
            niveles = [[]]
            colas = []
            for p in raices_lado:
                niveles[0].append(_slot(p))
                colas.append((
                    niveles_alimentadores(p.get("equipo_local_id"),
                                          p.get("equipo_local_nombre"), k),
                    niveles_alimentadores(p.get("equipo_visitante_id"),
                                          p.get("equipo_visitante_nombre"), k),
                ))
            profundidad = max((len(a) for izq_der in colas for a in izq_der), default=0)
            for j in range(profundidad):
                nivel = []
                for izq, der in colas:
                    nivel += izq[j] if j < len(izq) else []
                    nivel += der[j] if j < len(der) else []
                niveles.append(nivel)
            return niveles

        niveles_izq = lado_de(raices[:mitad])
        niveles_der = lado_de(raices[mitad:])
        ronda_de_nivel = lambda j: k - j              # nivel 0 = ronda k
        # La final "virtual" quedará log2(raices) rondas más adelante: así los
        # títulos (Cuartos, Semis...) salen bien aunque la final no exista aún.
        k_virtual = k + math.ceil(math.log2(len(raices)))

    def columnas(niveles):
        cols = []
        for j, slots in enumerate(niveles):
            if not slots:
                continue
            distancia = k_virtual - ronda_de_nivel(j)
            cols.append({"titulo": _nombre_ronda(distancia), "slots": slots})
        return list(reversed(cols))                    # ronda 1 primero

    return {
        "lados": {"izquierda": columnas(niveles_izq),
                  "derecha": columnas(niveles_der)},
        "final": final,
        "campeon": campeon,
    }
