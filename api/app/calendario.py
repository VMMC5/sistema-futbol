"""Generadores puros de calendario. Sin BD: reciben ids, devuelven cruces.

- Liga: round-robin por el método del círculo, ida y vuelta (la vuelta espeja
  cada jornada con la localía invertida).
- Eliminación directa: para que las llaves cuadren hasta la final, el número
  de participantes de la ronda 2 debe ser potencia de 2. Con n inscritos se
  dan `siguiente_potencia_de_2(n) - n` byes al azar (solo en la ronda 1); el
  resto se baraja y se empareja.
"""
import random
import unicodedata


def normalizar_tipo(tipo: str | None) -> str | None:
    """'  Eliminación   Directa ' -> 'eliminacion directa'."""
    if not tipo:
        return None
    plano = unicodedata.normalize("NFD", tipo)
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return " ".join(plano.lower().split())


def siguiente_potencia_de_2(n: int) -> int:
    return 1 if n <= 1 else 1 << (n - 1).bit_length()


def generar_liga(equipos: list[int]) -> list[list[tuple[int, int]]]:
    """Jornadas de ida + vuelta. Impar: se añade un fantasma (None) y quien
    le toca descansa esa jornada."""
    rueda = list(equipos)
    if len(rueda) % 2 == 1:
        rueda.append(None)
    n = len(rueda)
    ida = []
    for _ in range(n - 1):
        jornada = []
        for k in range(n // 2):
            a, b = rueda[k], rueda[n - 1 - k]
            if a is not None and b is not None:
                jornada.append((a, b))
        ida.append(jornada)
        # rota todos menos el primero
        rueda = [rueda[0]] + [rueda[-1]] + rueda[1:-1]
    vuelta = [[(v, l) for (l, v) in jornada] for jornada in ida]
    return ida + vuelta


def generar_ronda_eliminacion(
    equipos: list[int], rng: random.Random
) -> tuple[list[int], list[tuple[int, int]]]:
    """(byes, parejas). El rng se inyecta para poder probar determinista."""
    ids = list(equipos)
    rng.shuffle(ids)
    n_byes = siguiente_potencia_de_2(len(ids)) - len(ids)
    byes, juegan = ids[:n_byes], ids[n_byes:]
    parejas = [(juegan[i], juegan[i + 1]) for i in range(0, len(juegan), 2)]
    return byes, parejas
