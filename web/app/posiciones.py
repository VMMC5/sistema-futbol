"""
Traducción de una formación a filas de jugadores, de defensa a ataque.
Fuente canónica: FORMACIONES en mobile/src/screens/coach/LineupScreen.js.
Solo estas tres formaciones existen en el sistema.
"""
FORMACIONES = {
    "4-4-2": [1, 4, 4, 2],
    "4-3-3": [1, 4, 3, 3],
    "3-5-2": [1, 3, 5, 2],
}


def filas_desde_plan(formacion, titulares):
    """titulares: lista de dicts con 'orden'. Devuelve [[j, ...], ...] por línea.
    Los jugadores se reparten en orden (portero primero) según la formación.

    La app móvil (único cliente que guarda planes) limita los huecos a exactamente
    el tamaño de la formación, así que en la práctica len(titulares) <= suma(tam).
    Aun así, si un cliente distinto enviara MÁS jugadores que los que caben, los
    sobrantes se añaden a la última línea en vez de descartarse en silencio: mejor
    una cancha con una fila cargada que perder jugadores sin aviso."""
    tam = FORMACIONES.get(formacion, FORMACIONES["4-4-2"])
    orden = sorted(titulares, key=lambda j: j.get("orden", 0))
    filas, i = [], 0
    for n in tam:
        filas.append(orden[i:i + n])
        i += n
    if i < len(orden):            # sobrantes: no dejar a nadie fuera
        filas[-1].extend(orden[i:])
    return filas
